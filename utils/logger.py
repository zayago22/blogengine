"""
BlogEngine - Configuración de logging centralizado.
"""
import logging
import sys
from rich.logging import RichHandler

from config import get_settings


def setup_logging():
    """Configura logging para toda la aplicación."""
    settings = get_settings()
    level = logging.DEBUG if settings.app_debug else logging.INFO

    # Formato
    logging.basicConfig(
        level=level,
        format="%(name)s - %(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                rich_tracebacks=True,
                show_path=False,
                markup=True,
            )
        ],
    )

    # Reducir ruido de librerías externas
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logger = logging.getLogger("blogengine")
    logger.info("BlogEngine - Logging configurado")
    return logger
