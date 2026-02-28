"""
BlogEngine - Configuración centralizada.
Carga variables de entorno y config.yaml.
"""
import yaml
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Configuración desde variables de entorno."""

    # App
    app_name: str = "BlogEngine"
    app_env: str = "development"
    app_debug: bool = True
    app_secret_key: str = "cambiar-en-produccion"
    app_url: str = "http://localhost:8000"

    # Base de datos
    database_url: str = "sqlite+aiosqlite:///./blogengine.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # BlogEngine
    blogengine_base_url: str = "http://localhost:8000"
    admin_key: str = "blogengine-admin-secret-change-me"

    # Dashboard admin auth
    admin_user: str = "admin"
    admin_password: str = "admin"

    # DeepSeek
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"

    # Anthropic (Claude)
    anthropic_api_key: str = ""

    # Encriptación
    fernet_key: str = ""

    # Meta (Facebook + Instagram)
    meta_app_id: str = ""
    meta_app_secret: str = ""

    # LinkedIn
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""

    # Twitter/X
    twitter_api_key: str = ""
    twitter_api_secret: str = ""

    # Pinterest
    pinterest_app_id: str = ""
    pinterest_app_secret: str = ""

    # Google
    google_client_id: str = ""
    google_client_secret: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # Unsplash
    unsplash_access_key: str = ""

    # SMTP
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_name: str = "BlogEngine"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    """Retorna instancia cacheada de configuración."""
    return Settings()


def load_config() -> dict:
    """Carga configuración desde config.yaml."""
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


@lru_cache
def get_config() -> dict:
    """Retorna configuración YAML cacheada."""
    return load_config()
