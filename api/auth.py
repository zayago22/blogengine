"""
BlogEngine - Autenticación del dashboard admin.
Sesión basada en cookie firmada con HMAC.
"""
import hmac
import hashlib
import logging
from fastapi import Request
from config import get_settings

logger = logging.getLogger(__name__)


class RequiresLoginException(Exception):
    """Lanzada cuando una ruta protegida no tiene sesión válida."""
    pass


def create_session_token() -> str:
    """Genera el token de sesión esperado a partir de las credenciales configuradas."""
    s = get_settings()
    msg = f"{s.admin_user}:{s.admin_password}"
    return hmac.new(s.app_secret_key.encode(), msg.encode(), hashlib.sha256).hexdigest()


def verify_session_token(token: str | None) -> bool:
    """Verifica si el token de cookie es válido."""
    if not token:
        return False
    expected = create_session_token()
    return hmac.compare_digest(token, expected)


async def require_auth(request: Request) -> None:
    """Dependency que protege rutas del dashboard. Redirige a /admin/login si no autenticado."""
    token = request.cookies.get("session_token")
    if not verify_session_token(token):
        logger.warning(f"[Auth] Acceso denegado a {request.url.path}")
        raise RequiresLoginException()
