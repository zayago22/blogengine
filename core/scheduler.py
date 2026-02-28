"""
BlogEngine - Scheduler: dispatcher de pipelines diarios.

Define la tarea `dispatch_daily_pipelines` que:
1. Consulta todos los clientes activos en la BD.
2. Lanza task_daily_pipeline.delay(client.id) para cada uno.

Registrada en el Beat schedule de Celery (core/celery_app.py) para correr
a las 8:00 AM todos los días.
"""
import logging

from sqlalchemy import select

from core.celery_app import celery_app, run_async
from models.base import async_session
from models.client import Client

logger = logging.getLogger("blogengine.scheduler")


async def _dispatch_pipelines_async():
    """Obtiene todos los clientes activos y dispara su pipeline diario."""
    from core.task_wrappers import task_daily_pipeline

    async with async_session() as session:
        result = await session.execute(select(Client))
        clients = result.scalars().all()

    dispatched = 0
    for client in clients:
        try:
            task_daily_pipeline.delay(client.id)
            dispatched += 1
            logger.info("[Scheduler] Pipeline diario encolado → %s (id=%d)", client.nombre, client.id)
        except Exception as exc:
            logger.error("[Scheduler] Error encolando pipeline para %s: %s", client.nombre, exc)

    logger.info("[Scheduler] dispatch_daily_pipelines: %d clientes encolados", dispatched)
    return dispatched


@celery_app.task(name="core.scheduler.dispatch_daily_pipelines")
def dispatch_daily_pipelines():
    """
    Dispatcher periódico: lanza task_daily_pipeline para TODOS los clientes activos.
    Registrada en Beat schedule → corre a las 8:00 AM diariamente (America/Mexico_City).
    """
    logger.info("[Celery] dispatch_daily_pipelines: iniciando...")
    count = run_async(_dispatch_pipelines_async())
    logger.info("[Celery] dispatch_daily_pipelines: %d tareas encoladas", count or 0)
