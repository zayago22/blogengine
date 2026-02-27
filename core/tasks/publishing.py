"""
BlogEngine - Tareas Celery de publicación automática.
"""
import logging
from datetime import datetime

from sqlalchemy import select

from core.celery_app import celery_app, run_async
from models.base import async_session
from models.blog_post import BlogPost

logger = logging.getLogger("blogengine.tasks.publishing")


# ---------------------------------------------------------------------------

async def _auto_publish_scheduled_async() -> dict:
    """Publica todos los posts aprobados cuya fecha programada ya llegó."""
    published_count = 0
    post_ids = []

    async with async_session() as session:
        now = datetime.utcnow()
        result = await session.execute(
            select(BlogPost).where(
                BlogPost.estado == "aprobado",
                BlogPost.fecha_programada.isnot(None),
                BlogPost.fecha_programada <= now,
            )
        )
        posts = result.scalars().all()

        for post in posts:
            try:
                post.estado = "publicado"
                post.fecha_publicado = datetime.utcnow()
                await session.commit()

                logger.info(
                    "[Celery] Publicado automáticamente: '%s' (client_id=%d)",
                    post.titulo, post.client_id,
                )

                # Ping al sitemap del cliente
                from core.tasks.seo_ping import ping_client_sitemap
                ping_client_sitemap.delay(post.client_id)

                published_count += 1
                post_ids.append(post.id)

            except Exception as e:
                await session.rollback()
                logger.error(
                    "[Celery] Error publicando post_id=%d: %s", post.id, e
                )

    return {"published_count": published_count, "post_ids": post_ids}


@celery_app.task(name="core.tasks.publishing.auto_publish_scheduled")
def auto_publish_scheduled() -> dict:
    """
    Tarea periódica: publica automáticamente todos los posts aprobados
    con fecha_programada <= ahora.
    Disparada por Celery Beat cada hora en punto.
    """
    logger.info("[Celery] Iniciando auto-publicación de posts programados")
    result = run_async(_auto_publish_scheduled_async())
    logger.info(
        "[Celery] Auto-publicación finalizada: %d posts publicados",
        result.get("published_count", 0),
    )
    return result


# ---------------------------------------------------------------------------

async def _publish_single_async(post_id: int) -> dict:
    async with async_session() as session:
        post = await session.get(BlogPost, post_id)
        if not post:
            return {"success": False, "error": f"Post #{post_id} no encontrado"}

        if post.estado != "aprobado":
            return {
                "success": False,
                "error": f"Post #{post_id} no está aprobado (estado actual: '{post.estado}')",
            }

        post.estado = "publicado"
        post.fecha_publicado = datetime.utcnow()
        await session.commit()

        logger.info(
            "[Celery] Post publicado manualmente: '%s' (post_id=%d, client_id=%d)",
            post.titulo, post.id, post.client_id,
        )

        from core.tasks.seo_ping import ping_client_sitemap
        ping_client_sitemap.delay(post.client_id)

        return {"success": True, "post_id": post_id}


@celery_app.task(name="core.tasks.publishing.publish_single")
def publish_single(post_id: int) -> dict:
    """
    Publica un post específico por su ID.
    El post debe estar en estado 'aprobado'.
    """
    logger.info("[Celery] publish_single post_id=%d", post_id)
    return run_async(_publish_single_async(post_id))


# ---------------------------------------------------------------------------

async def _unpublish_single_async(post_id: int) -> dict:
    async with async_session() as session:
        post = await session.get(BlogPost, post_id)
        if not post:
            return {"success": False, "error": f"Post #{post_id} no encontrado"}

        post.estado = "despublicado"
        await session.commit()

        logger.info(
            "[Celery] Post despublicado: '%s' (post_id=%d, client_id=%d)",
            post.titulo, post.id, post.client_id,
        )

        return {"success": True, "post_id": post_id}


@celery_app.task(name="core.tasks.publishing.unpublish_single")
def unpublish_single(post_id: int) -> dict:
    """Despublica un post específico por su ID."""
    logger.info("[Celery] unpublish_single post_id=%d", post_id)
    return run_async(_unpublish_single_async(post_id))
