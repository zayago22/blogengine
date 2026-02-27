"""
Celery tasks for editorial calendar generation.
Beat schedule: day 1 of each month at 7AM
"""
import json
import logging
import calendar
from datetime import date, timedelta

from core.celery_app import celery_app, run_async
from models.base import async_session as AsyncSessionLocal

logger = logging.getLogger("blogengine.tasks.calendar_gen")

PLAN_LIMITS = {
    "free": 2,
    "starter": 8,
    "pro": 20,
    "agency": 50,
}

MONTH_NAMES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def _first_monday_of_month(year: int, mes: int) -> date:
    """Returns the first Monday of a given month/year."""
    d = date(year, mes, 1)
    # Monday = 0 in weekday()
    days_until_monday = (7 - d.weekday()) % 7
    return d + timedelta(days=days_until_monday)


def _build_prompt(client, money_pages, keywords, n_articles, nombre_mes, año) -> str:
    money_list = "\n".join(
        f"  - {mp.url} - {mp.titulo}" for mp in money_pages
    ) or "  (sin money pages registradas)"

    kw_list = "\n".join(
        f"  - {kw.keyword} - volume:{kw.search_volume} - difficulty:{kw.difficulty}"
        for kw in keywords[:n_articles]
    )

    return (
        f"Eres un estratega de contenido SEO. Genera un calendario editorial para el mes de {nombre_mes} {año}.\n\n"
        f"Cliente: {client.nombre} - Industria: {client.industria}\n"
        f"Sitio web: {client.sitio_web}\n"
        f"Money pages:\n{money_list}\n\n"
        f"Keywords disponibles (priorizadas):\n{kw_list}\n\n"
        f"Genera un calendario con {n_articles} artículos distribuidos en 4 semanas.\n"
        f"Para cada artículo:\n"
        f"- titulo_sugerido: título SEO con la keyword al inicio\n"
        f"- keyword_principal: la keyword exacta de la lista\n"
        f"- semana_del_mes: 1, 2, 3 o 4\n"
        f"- prioridad: alta/media/baja\n"
        f"- notas: qué money page linkear y por qué\n\n"
        f'Responde SOLO en JSON válido:\n'
        f'{{"entries": [{{"titulo_sugerido": "...", "keyword_principal": "...", '
        f'"semana_del_mes": 1, "prioridad": "alta", "notas": "..."}}]}}'
    )


def _clean_json(raw: str) -> str:
    """Strip markdown code fences if present."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        # Remove first and last fence lines
        lines = lines[1:] if lines[0].startswith("```") else lines
        lines = lines[:-1] if lines and lines[-1].strip() == "```" else lines
        raw = "\n".join(lines).strip()
    return raw


async def _generate_for_client(client_id: int, mes: int, año: int, delete_pending: bool = False):
    """Core async logic shared by both tasks."""
    from models.client import Client
    from models.seo_strategy import SEOKeyword, MoneyPage
    from models.calendar import CalendarEntry
    from core.ai_router import AIRouter
    from sqlalchemy import select, delete as sa_delete, and_, extract

    async with AsyncSessionLocal() as session:  # noqa: SIM117
        # Load client
        result = await session.execute(select(Client).where(Client.id == client_id))
        client = result.scalar_one_or_none()
        if not client:
            logger.warning("[Celery] Cliente %d no encontrado", client_id)
            return 0

        # Optionally delete existing pending entries for this month/year
        if delete_pending:
            await session.execute(
                sa_delete(CalendarEntry).where(
                    and_(
                        CalendarEntry.client_id == client_id,
                        CalendarEntry.estado == "pendiente",
                        extract("month", CalendarEntry.fecha_programada) == mes,
                        extract("year", CalendarEntry.fecha_programada) == año,
                    )
                )
            )
            await session.commit()
            logger.info("[Celery] Entradas pendientes eliminadas para cliente %d (%d/%d)", client_id, mes, año)

        # Plan limits
        n_articles = PLAN_LIMITS.get(client.plan, 2)

        # Keywords pendientes ordenadas por prioridad DESC
        kw_result = await session.execute(
            select(SEOKeyword)
            .where(
                SEOKeyword.client_id == client_id,
                SEOKeyword.estado == "pendiente",
            )
            .order_by(SEOKeyword.prioridad.desc())
            .limit(n_articles)
        )
        keywords = kw_result.scalars().all()

        if not keywords:
            logger.info("[Celery] Sin keywords pendientes para cliente %d (%s), skip", client_id, client.nombre)
            return 0

        # Money pages
        mp_result = await session.execute(
            select(MoneyPage).where(MoneyPage.client_id == client_id)
        )
        money_pages = mp_result.scalars().all()

        nombre_mes = MONTH_NAMES_ES.get(mes, str(mes))
        prompt = _build_prompt(client, money_pages, keywords, n_articles, nombre_mes, año)

        # Call AI — retry once on JSON parse failure
        ai_router = AIRouter()
        raw_response = None
        entries = None

        for attempt in range(2):
            try:
                raw_response = await ai_router.generate(
                    task_name="estrategia_editorial",
                    prompt=prompt,
                    session=session,
                )
                cleaned = _clean_json(raw_response)
                data = json.loads(cleaned)
                entries = data.get("entries", [])
                break
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                if attempt == 0:
                    logger.warning(
                        "[Celery] JSON parsing falló (intento 1) para cliente %d: %s — reintentando",
                        client_id, exc,
                    )
                else:
                    logger.error(
                        "[Celery] JSON parsing falló (intento 2) para cliente %d: %s — abortando",
                        client_id, exc,
                    )
                    return 0

        if not entries:
            logger.warning("[Celery] IA devolvió 0 entradas para cliente %d", client_id)
            return 0

        # Build keyword lookup by keyword text
        kw_lookup = {kw.keyword.lower(): kw for kw in keywords}

        # First Monday of the target month
        first_monday = _first_monday_of_month(año, mes)

        created = 0
        for entry in entries:
            try:
                semana = int(entry.get("semana_del_mes", 1))
                semana = max(1, min(4, semana))  # clamp 1-4
                fecha = first_monday + timedelta(days=(semana - 1) * 7)

                keyword_text = entry.get("keyword_principal", "")
                matched_kw = kw_lookup.get(keyword_text.lower())
                keyword_id = matched_kw.id if matched_kw else None

                calendar_entry = CalendarEntry(
                    client_id=client_id,
                    keyword_id=keyword_id,
                    titulo_sugerido=entry.get("titulo_sugerido", ""),
                    keyword_principal=keyword_text,
                    fecha_programada=fecha,
                    semana_del_mes=semana,
                    prioridad=entry.get("prioridad", "media"),
                    estado="pendiente",
                    notas=entry.get("notas", ""),
                )
                session.add(calendar_entry)
                created += 1
            except Exception as exc:
                logger.warning("[Celery] Error creando CalendarEntry: %s — entry: %s", exc, entry)

        await session.commit()
        logger.info("[Celery] Calendario generado para %s: %d entradas", client.nombre, created)
        return created


@celery_app.task(name="generate_calendars")
def generate_calendars():
    """
    Runs on day 1 of each month (7AM).
    Generates editorial calendars for all active clients.
    """
    from datetime import date as _date
    from models.client import Client
    from sqlalchemy import select

    today = _date.today()
    # Generate calendar for the current month
    mes = today.month
    año = today.year

    logger.info("[Celery] Iniciando generación de calendarios para %s/%d", MONTH_NAMES_ES.get(mes), año)

    async def _run_all():
        from models.base import async_session as _ASL
        async with _ASL() as session:
            result = await session.execute(select(Client))
            clients = result.scalars().all()

        total = 0
        for client in clients:
            try:
                count = await _generate_for_client(client.id, mes, año, delete_pending=False)
                total += count
            except Exception as exc:
                logger.error("[Celery] Error generando calendario para cliente %d: %s", client.id, exc)

        logger.info("[Celery] Calendarios completados: %d entradas totales en %d clientes", total, len(clients))

    run_async(_run_all())


@celery_app.task(name="generate_client_calendar")
def generate_client_calendar(client_id: int, mes: int, año: int):
    """
    Generates editorial calendar for a specific client and month/year.
    Deletes existing 'pendiente' entries for that month before generating.
    """
    logger.info(
        "[Celery] Generando calendario para cliente %d — %s/%d",
        client_id, MONTH_NAMES_ES.get(mes, str(mes)), año,
    )

    async def _run():
        return await _generate_for_client(client_id, mes, año, delete_pending=True)

    count = run_async(_run())
    logger.info("[Celery] Calendario cliente %d: %d entradas creadas", client_id, count)
    return {"client_id": client_id, "mes": mes, "año": año, "entradas_creadas": count}
