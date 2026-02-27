"""
BlogEngine - Tareas Celery de ping a buscadores (Google, Bing).
"""
import logging
import os

import httpx
from sqlalchemy import select

from core.celery_app import celery_app, run_async
from models.base import async_session
from models.client import Client

logger = logging.getLogger("blogengine.tasks.seo_ping")

BASE_URL = os.environ.get("BLOGENGINE_BASE_URL", "http://localhost:8000")


# ---------------------------------------------------------------------------

async def _ping_sitemap(sitemap_url: str) -> dict:
    """Hace ping a Google y Bing con la URL del sitemap. Retorna los status codes."""
    google_status = 0
    bing_status = 0
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(
                "https://www.google.com/ping", params={"sitemap": sitemap_url}
            )
            google_status = r.status_code
        except Exception as e:
            logger.warning("[Celery] Google ping error (%s): %s", sitemap_url, e)

        try:
            r = await client.get(
                "https://www.bing.com/ping", params={"sitemap": sitemap_url}
            )
            bing_status = r.status_code
        except Exception as e:
            logger.warning("[Celery] Bing ping error (%s): %s", sitemap_url, e)

    return {"google": google_status, "bing": bing_status}


async def _ping_all_clients_async() -> dict:
    pinged_count = 0
    results = []

    async with async_session() as session:
        result = await session.execute(
            select(Client).where(Client.blog_slug.isnot(None), Client.blog_slug != "")
        )
        clients = result.scalars().all()

        for client in clients:
            try:
                sitemap_url = f"{BASE_URL}/b/{client.blog_slug}/sitemap.xml"
                ping = await _ping_sitemap(sitemap_url)

                logger.info(
                    "[Celery] Ping SEO para %s: Google=%d, Bing=%d",
                    client.nombre, ping["google"], ping["bing"],
                )

                pinged_count += 1
                results.append({
                    "client_id": client.id,
                    "nombre": client.nombre,
                    "sitemap_url": sitemap_url,
                    **ping,
                })
            except Exception as e:
                logger.error(
                    "[Celery] Error en ping para cliente %s: %s", client.nombre, e
                )

    return {"pinged_count": pinged_count, "results": results}


@celery_app.task(name="core.tasks.seo_ping.ping_all_clients")
def ping_all_clients() -> dict:
    """
    Tarea periódica: hace ping a Google y Bing con el sitemap de cada cliente.
    Disparada por Celery Beat cada lunes a las 8:00 AM.
    """
    logger.info("[Celery] Iniciando ping SEO para todos los clientes")
    result = run_async(_ping_all_clients_async())
    logger.info(
        "[Celery] Ping SEO finalizado: %d clientes notificados",
        result.get("pinged_count", 0),
    )
    return result


# ---------------------------------------------------------------------------

async def _ping_client_sitemap_async(client_id: int) -> dict:
    async with async_session() as session:
        client = await session.get(Client, client_id)
        if not client or not client.blog_slug:
            return {"success": False, "error": f"Cliente #{client_id} no encontrado o sin blog_slug"}

        sitemap_url = f"{BASE_URL}/b/{client.blog_slug}/sitemap.xml"
        ping = await _ping_sitemap(sitemap_url)

        logger.info(
            "[Celery] Ping SEO para %s: Google=%d, Bing=%d",
            client.nombre, ping["google"], ping["bing"],
        )

        return {"success": True, **ping}


@celery_app.task(name="core.tasks.seo_ping.ping_client_sitemap")
def ping_client_sitemap(client_id: int) -> dict:
    """
    Ping individual a Google y Bing para un cliente específico.
    Se dispara automáticamente después de publicar un post.
    """
    logger.info("[Celery] ping_client_sitemap client_id=%d", client_id)
    return run_async(_ping_client_sitemap_async(client_id))
