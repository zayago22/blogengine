"""
BlogEngine - Configuración de Celery.
Worker asíncrono para tareas periódicas y en background.
"""
import asyncio
import os

from celery import Celery
from celery.schedules import crontab

# --- Instancia principal ---
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("blogengine")

celery_app.conf.update(
    broker_url=REDIS_URL,
    result_backend=REDIS_URL,
    timezone="America/Mexico_City",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    broker_connection_timeout=5,
    broker_connection_retry_on_startup=False,
    redis_socket_connect_timeout=5,
    redis_socket_timeout=5,
)

# --- Auto-discover de tareas ---
celery_app.autodiscover_tasks(["core.tasks", "core.task_wrappers", "core.scheduler"])

# --- Beat schedule (tareas periódicas) ---
celery_app.conf.beat_schedule = {
    # Genera artículos programados todos los días a las 6:00 AM
    "generate-scheduled-posts": {
        "task": "core.tasks.generation.generate_scheduled_posts",
        "schedule": crontab(hour=6, minute=0),
    },
    # Auto-publica posts aprobados cada hora (en punto)
    "auto-publish-posts": {
        "task": "core.tasks.publishing.auto_publish_scheduled",
        "schedule": crontab(minute=0),
    },
    # Ping a Google/Bing cada lunes a las 8:00 AM
    "ping-search-engines": {
        "task": "core.tasks.seo_ping.ping_all_clients",
        "schedule": crontab(hour=8, minute=0, day_of_week=1),
    },
    # Distribuye posts a redes sociales cada 2 horas
    "distribute-social": {
        "task": "core.tasks.social.distribute_pending",
        "schedule": crontab(minute=0, hour="*/2"),
    },
    # Genera calendarios de contenido el día 1 de cada mes a las 7:00 AM
    "generate-monthly-calendars": {
        "task": "core.tasks.calendar_gen.generate_calendars",
        "schedule": crontab(hour=7, minute=0, day_of_month=1),
    },
    # Dispatcher: lanza pipeline diario para TODOS los clientes a las 8:00 AM
    "dispatch-daily-pipelines": {
        "task": "core.scheduler.dispatch_daily_pipelines",
        "schedule": crontab(hour=8, minute=0),
    },
}


# --- Helper para ejecutar coroutines async desde tareas síncronas de Celery ---
def run_async(coro):
    """
    Ejecuta una coroutine async desde un contexto síncrono (Celery worker).
    Necesario porque SQLAlchemy usa async pero Celery es síncrono.

    Uso:
        @celery_app.task
        def my_task():
            result = run_async(some_async_function())
            return result
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
