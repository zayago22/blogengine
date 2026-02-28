"""
BlogEngine - Wrapper unificado de tareas Celery.

Expone las tareas principales para poder importarlas desde cualquier módulo:
    from core.tasks import task_research_keywords, task_generate_article
    task_research_keywords.delay(client_id)
"""
import logging

from sqlalchemy import select, func

from core.celery_app import celery_app, run_async
from models.base import async_session
from models.client import Client
from models.blog_post import BlogPost
from models.seo_strategy import SEOKeyword, MoneyPage

logger = logging.getLogger("blogengine.tasks")


# ---------------------------------------------------------------------------
# TAREA: Investigar keywords del cliente con IA
# ---------------------------------------------------------------------------

async def _research_keywords_async(client_id: int):
    """Lógica async de keyword research para un cliente."""
    from core.content_engine import ContentEngine

    async with async_session() as session:
        client = await session.get(Client, client_id)
        if not client:
            logger.warning("[tasks] Cliente %d no encontrado", client_id)
            return

        # Verificar que tenga money pages antes de investigar
        mp_result = await session.execute(
            select(func.count(MoneyPage.id)).where(
                MoneyPage.client_id == client_id,
                MoneyPage.activa == True,
            )
        )
        if (mp_result.scalar() or 0) == 0:
            logger.info(
                "[tasks] %s: sin money pages activas, saltando research",
                client.nombre,
            )
            return

        try:
            engine = ContentEngine(db=session)
            strategy = await engine.research_keywords(client, num_keywords=20)
            kw_count = sum(
                len(c.get("keywords", [])) + 1
                for c in strategy.get("clusters", [])
            )
            logger.info(
                "[tasks] %s: research completado → %d keywords generadas",
                client.nombre, kw_count,
            )
        except Exception as exc:
            logger.error(
                "[tasks] %s: error en research: %s", client.nombre, exc
            )


@celery_app.task(name="core.tasks.task_research_keywords")
def task_research_keywords(client_id: int):
    """
    Investiga y genera keywords SEO para un cliente usando IA.
    Se dispara automáticamente al crear un nuevo cliente.
    """
    logger.info("[Celery] task_research_keywords → cliente %d", client_id)
    run_async(_research_keywords_async(client_id))


# ---------------------------------------------------------------------------
# TAREA: Generar un artículo para la keyword de mayor prioridad
# ---------------------------------------------------------------------------

async def _generate_article_async(client_id: int):
    """Genera un artículo para la keyword pendiente de mayor prioridad."""
    from core.content_engine import ContentEngine

    async with async_session() as session:
        client = await session.get(Client, client_id)
        if not client:
            logger.warning("[tasks] Cliente %d no encontrado", client_id)
            return

        # Buscar keyword pendiente de mayor prioridad
        kw_result = await session.execute(
            select(SEOKeyword)
            .where(
                SEOKeyword.client_id == client_id,
                SEOKeyword.estado == "pendiente",
            )
            .order_by(SEOKeyword.prioridad.desc())
            .limit(1)
        )
        keyword = kw_result.scalar_one_or_none()

        if not keyword:
            logger.info("[tasks] %s: sin keywords pendientes", client.nombre)
            return

        keyword.estado = "en_progreso"
        await session.flush()

        try:
            engine = ContentEngine(db=session)
            await engine.generate_for_keyword(client=client, keyword_id=keyword.id)
            keyword.estado = "publicado"
            await session.commit()
            logger.info(
                "[tasks] %s: artículo generado para '%s'",
                client.nombre, keyword.keyword,
            )
        except Exception as exc:
            await session.rollback()
            keyword.estado = "pendiente"
            await session.commit()
            logger.error(
                "[tasks] %s: error generando '%s': %s",
                client.nombre, keyword.keyword, exc,
            )


@celery_app.task(name="core.tasks.task_generate_article")
def task_generate_article(client_id: int):
    """
    Genera un artículo SEO para la keyword pendiente de mayor prioridad del cliente.
    """
    logger.info("[Celery] task_generate_article → cliente %d", client_id)
    run_async(_generate_article_async(client_id))


# ---------------------------------------------------------------------------
# TAREA: Publicar un post aprobado
# ---------------------------------------------------------------------------

async def _auto_publish_async(post_id: int):
    """Publica un post aprobado por su ID."""
    from core.content_engine import ContentEngine

    async with async_session() as session:
        post = await session.get(BlogPost, post_id)
        if not post:
            logger.warning("[tasks] Post %d no encontrado", post_id)
            return

        if post.estado != "aprobado":
            logger.info("[tasks] Post %d no está aprobado (estado=%s)", post_id, post.estado)
            return

        try:
            post.estado = "publicado"
            from datetime import datetime, timezone
            post.fecha_publicado = datetime.now(timezone.utc)
            await session.commit()
            logger.info("[tasks] Post %d publicado", post_id)
        except Exception as exc:
            await session.rollback()
            logger.error("[tasks] Error publicando post %d: %s", post_id, exc)


@celery_app.task(name="core.tasks.task_auto_publish")
def task_auto_publish(post_id: int):
    """
    Publica un post aprobado (estado aprobado → publicado).
    """
    logger.info("[Celery] task_auto_publish → post %d", post_id)
    run_async(_auto_publish_async(post_id))


# ---------------------------------------------------------------------------
# TAREA: Pipeline diario completo para un cliente
# ---------------------------------------------------------------------------

async def _daily_pipeline_async(client_id: int):
    """
    Orquesta el pipeline completo para un cliente:
    1. Si no hay keywords → research
    2. Si hay keywords sin artículo → generar artículo
    3. Si hay artículos aprobados → publicar
    """
    from core.content_engine import ContentEngine

    async with async_session() as session:
        client = await session.get(Client, client_id)
        if not client:
            logger.warning("[tasks] Cliente %d no encontrado", client_id)
            return

        # 1. Verificar si tiene keywords
        kw_count_result = await session.execute(
            select(func.count(SEOKeyword.id)).where(SEOKeyword.client_id == client_id)
        )
        kw_count = kw_count_result.scalar() or 0

        if kw_count == 0:
            # Sin keywords → hacer research primero
            mp_result = await session.execute(
                select(func.count(MoneyPage.id)).where(
                    MoneyPage.client_id == client_id,
                    MoneyPage.activa == True,
                )
            )
            if (mp_result.scalar() or 0) > 0:
                logger.info("[tasks pipeline] %s: sin keywords, iniciando research", client.nombre)
                engine = ContentEngine(db=session)
                await engine.research_keywords(client, num_keywords=20)
            else:
                logger.info("[tasks pipeline] %s: sin money pages, pipeline omitido", client.nombre)
            return

        # 2. Buscar keyword pendiente → generar artículo
        kw_result = await session.execute(
            select(SEOKeyword)
            .where(
                SEOKeyword.client_id == client_id,
                SEOKeyword.estado == "pendiente",
            )
            .order_by(SEOKeyword.prioridad.desc())
            .limit(1)
        )
        keyword = kw_result.scalar_one_or_none()

        if keyword:
            keyword.estado = "en_progreso"
            await session.flush()
            try:
                engine = ContentEngine(db=session)
                await engine.generate_for_keyword(client=client, keyword_id=keyword.id)
                keyword.estado = "publicado"
                await session.commit()
                logger.info("[tasks pipeline] %s: artículo generado → '%s'", client.nombre, keyword.keyword)
            except Exception as exc:
                await session.rollback()
                keyword.estado = "pendiente"
                await session.commit()
                logger.error("[tasks pipeline] %s: error generando: %s", client.nombre, exc)
            return

        # 3. Publicar posts aprobados
        from datetime import datetime, timezone
        approved_result = await session.execute(
            select(BlogPost)
            .where(
                BlogPost.client_id == client_id,
                BlogPost.estado == "aprobado",
            )
            .limit(3)
        )
        approved_posts = approved_result.scalars().all()

        for post in approved_posts:
            try:
                post.estado = "publicado"
                post.fecha_publicado = datetime.now(timezone.utc)
                await session.commit()
                logger.info("[tasks pipeline] %s: post %d publicado", client.nombre, post.id)
            except Exception as exc:
                await session.rollback()
                logger.error("[tasks pipeline] %s: error publicando post %d: %s", client.nombre, post.id, exc)


@celery_app.task(name="core.tasks.task_daily_pipeline")
def task_daily_pipeline(client_id: int):
    """
    Pipeline diario completo: research → generate → publish.
    Se ejecuta para cada cliente activo desde el Beat schedule.
    """
    logger.info("[Celery] task_daily_pipeline → cliente %d", client_id)
    run_async(_daily_pipeline_async(client_id))
