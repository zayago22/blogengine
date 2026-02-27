"""
BlogEngine - Tareas Celery de generación de artículos.
"""
import logging
from calendar import monthrange
from datetime import datetime

from sqlalchemy import select, func, extract

from core.celery_app import celery_app, run_async
from models.base import async_session
from models.client import Client
from models.blog_post import BlogPost
from models.seo_strategy import SEOKeyword

logger = logging.getLogger("blogengine.tasks.generation")

# Límites mensuales de artículos por plan
PLAN_LIMITS = {
    "free": 2,
    "starter": 8,
    "pro": 20,
    "agency": 50,
}


async def _generate_scheduled_posts_async():
    """Lógica async de generación programada para todos los clientes."""
    from core.content_engine import ContentEngine

    now = datetime.utcnow()
    first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    async with async_session() as session:
        # Obtener todos los clientes activos
        result = await session.execute(select(Client))
        clients = result.scalars().all()

        for client in clients:
            try:
                limit = PLAN_LIMITS.get(client.plan, 2)

                # Contar posts generados este mes
                count_result = await session.execute(
                    select(func.count(BlogPost.id)).where(
                        BlogPost.client_id == client.id,
                        BlogPost.created_at >= first_day,
                    )
                )
                count = count_result.scalar() or 0

                if count >= limit:
                    logger.info(
                        "[Celery] %s: límite mensual alcanzado (%d/%d)",
                        client.nombre, count, limit,
                    )
                    continue

                # Buscar la keyword pendiente de mayor prioridad
                kw_result = await session.execute(
                    select(SEOKeyword)
                    .where(
                        SEOKeyword.client_id == client.id,
                        SEOKeyword.estado == "pendiente",
                    )
                    .order_by(SEOKeyword.prioridad.desc())
                    .limit(1)
                )
                keyword = kw_result.scalar_one_or_none()

                if not keyword:
                    logger.info(
                        "[Celery] %s: sin keywords pendientes", client.nombre
                    )
                    continue

                # Marcar como en progreso antes de generar
                keyword.estado = "en_progreso"
                await session.flush()

                try:
                    engine = ContentEngine(db=session)
                    await engine.generate_for_keyword(
                        client=client, keyword_id=keyword.id
                    )
                    keyword.estado = "publicado"
                    await session.commit()
                    logger.info(
                        "[Celery] %s: artículo generado para '%s'",
                        client.nombre, keyword.keyword,
                    )
                except Exception as gen_err:
                    await session.rollback()
                    keyword.estado = "pendiente"
                    await session.commit()
                    logger.error(
                        "[Celery] %s: error generando '%s': %s",
                        client.nombre, keyword.keyword, gen_err,
                    )

            except Exception as client_err:
                logger.error(
                    "[Celery] Error procesando cliente %s: %s",
                    client.nombre, client_err,
                )


@celery_app.task(name="core.tasks.generation.generate_scheduled_posts")
def generate_scheduled_posts():
    """
    Tarea periódica: genera artículos automáticamente para todos los clientes
    según su plan y keywords pendientes.
    Disparada por Celery Beat cada día a las 6:00 AM.
    """
    logger.info("[Celery] Iniciando generación programada de posts")
    run_async(_generate_scheduled_posts_async())
    logger.info("[Celery] Generación programada finalizada")


# ---------------------------------------------------------------------------

async def _generate_single_article_async(client_id: int, keyword_id: int) -> dict:
    """Lógica async para generar un artículo de una sola keyword."""
    from core.content_engine import ContentEngine

    async with async_session() as session:
        client = await session.get(Client, client_id)
        if not client:
            return {"success": False, "error": f"Cliente #{client_id} no encontrado"}

        keyword = await session.get(SEOKeyword, keyword_id)
        if not keyword or keyword.client_id != client_id:
            return {"success": False, "error": f"Keyword #{keyword_id} no encontrada para este cliente"}

        try:
            keyword.estado = "en_progreso"
            await session.flush()

            engine = ContentEngine(db=session)
            result = await engine.generate_for_keyword(
                client=client, keyword_id=keyword_id
            )

            await session.commit()

            return {
                "success": True,
                "post_id": result.blog_post_id,
                "score": result.seo_score,
                "keyword": keyword.keyword,
            }
        except Exception as e:
            await session.rollback()
            keyword.estado = "pendiente"
            await session.commit()
            logger.error(
                "[Celery] generate_single_article error cliente=%d keyword=%d: %s",
                client_id, keyword_id, e,
            )
            return {"success": False, "error": str(e)}


@celery_app.task(name="core.tasks.generation.generate_single_article")
def generate_single_article(client_id: int, keyword_id: int) -> dict:
    """
    Genera un artículo para una keyword específica.
    Retorna {"success": True, "post_id": ..., "score": ...}
    o {"success": False, "error": "..."}.
    """
    logger.info(
        "[Celery] generate_single_article cliente=%d keyword=%d",
        client_id, keyword_id,
    )
    return run_async(_generate_single_article_async(client_id, keyword_id))


# ---------------------------------------------------------------------------

async def _generate_batch_async(client_id: int, count: int) -> list[int]:
    """Obtiene las N keywords pendientes de mayor prioridad."""
    async with async_session() as session:
        result = await session.execute(
            select(SEOKeyword)
            .where(
                SEOKeyword.client_id == client_id,
                SEOKeyword.estado == "pendiente",
            )
            .order_by(SEOKeyword.prioridad.desc())
            .limit(count)
        )
        return [kw.id for kw in result.scalars().all()]


@celery_app.task(name="core.tasks.generation.generate_batch")
def generate_batch(client_id: int, count: int = 5) -> list[str]:
    """
    Dispara generate_single_article para las N keywords pendientes de mayor prioridad.
    Retorna lista de task_ids Celery.
    """
    logger.info(
        "[Celery] generate_batch cliente=%d count=%d", client_id, count
    )
    keyword_ids = run_async(_generate_batch_async(client_id, count))

    task_ids = []
    for keyword_id in keyword_ids:
        task = generate_single_article.delay(client_id, keyword_id)
        task_ids.append(task.id)
        logger.info(
            "[Celery] Tarea disparada keyword=%d → task_id=%s", keyword_id, task.id
        )

    logger.info(
        "[Celery] generate_batch: %d tareas disparadas para cliente=%d",
        len(task_ids), client_id,
    )
    return task_ids
