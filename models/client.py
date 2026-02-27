"""
BlogEngine - Modelo de Cliente (tenant).
Cada cliente tiene su propia configuración de CMS, redes sociales y plan.
"""
from typing import Optional
from sqlalchemy import String, Boolean, Integer, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class Client(Base, TimestampMixin):
    """Modelo principal de cliente."""
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # --- Información básica ---
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    industria: Mapped[str] = mapped_column(String(100), nullable=False)
    sitio_web: Mapped[str] = mapped_column(String(500), nullable=False)

    # --- Marca y contenido ---
    tono_de_marca: Mapped[str] = mapped_column(
        String(50), default="profesional"
    )  # formal, casual, técnico, amigable, profesional
    palabras_clave_nicho: Mapped[Optional[dict]] = mapped_column(
        JSON, default=list
    )  # Lista de keywords principales
    audiencia_objetivo: Mapped[Optional[str]] = mapped_column(Text, default="")
    idioma: Mapped[str] = mapped_column(String(5), default="es")
    descripcion_negocio: Mapped[Optional[str]] = mapped_column(Text, default="")

    # --- Plan y facturación ---
    plan: Mapped[str] = mapped_column(
        String(20), default="free"
    )  # free, starter, pro, agency
    estado: Mapped[str] = mapped_column(
        String(20), default="activo"
    )  # activo, pausado, trial, cancelado
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(200))

    # --- CMS ---
    cms_type: Mapped[str] = mapped_column(
        String(50), default="wordpress"
    )  # wordpress, webflow, ghost, custom
    cms_url: Mapped[Optional[str]] = mapped_column(String(500))
    cms_credentials_encrypted: Mapped[Optional[str]] = mapped_column(
        Text
    )  # Encriptado con Fernet

    # --- Redes sociales (tokens encriptados) ---
    facebook_page_id: Mapped[Optional[str]] = mapped_column(String(200))
    facebook_token_encrypted: Mapped[Optional[str]] = mapped_column(Text)
    instagram_account_id: Mapped[Optional[str]] = mapped_column(String(200))
    instagram_token_encrypted: Mapped[Optional[str]] = mapped_column(Text)
    linkedin_org_id: Mapped[Optional[str]] = mapped_column(String(200))
    linkedin_token_encrypted: Mapped[Optional[str]] = mapped_column(Text)
    twitter_user_id: Mapped[Optional[str]] = mapped_column(String(200))
    twitter_token_encrypted: Mapped[Optional[str]] = mapped_column(Text)
    pinterest_board_id: Mapped[Optional[str]] = mapped_column(String(200))
    pinterest_token_encrypted: Mapped[Optional[str]] = mapped_column(Text)
    google_business_location_id: Mapped[Optional[str]] = mapped_column(String(200))
    google_business_token_encrypted: Mapped[Optional[str]] = mapped_column(Text)

    # --- Blog hospedado en BlogEngine ---
    blog_slug: Mapped[Optional[str]] = mapped_column(
        String(100), unique=True, index=True
    )  # mi-cliente → mi-cliente.blogengine.app
    blog_domain: Mapped[Optional[str]] = mapped_column(
        String(300), unique=True, index=True
    )  # blog.clientesite.com (dominio personalizado, CNAME)
    blog_design: Mapped[Optional[dict]] = mapped_column(
        JSON, default=dict
    )  # {primary, background, text, accent, font, logo_url}
    blog_cta_text: Mapped[Optional[str]] = mapped_column(
        String(300), default="Conoce nuestros servicios"
    )
    blog_cta_url: Mapped[Optional[str]] = mapped_column(String(500))

    # --- SEO ---
    seo_integration_level: Mapped[str] = mapped_column(
        String(20), default="subdomain"
    )  # subdirectory, subdomain, external
    seo_canonical_domain: Mapped[Optional[str]] = mapped_column(String(300))  # www.cliente.com
    seo_blog_base_url: Mapped[Optional[str]] = mapped_column(String(500))     # https://blog.cliente.com
    seo_proxy_path: Mapped[str] = mapped_column(String(100), default="/blog")
    seo_google_analytics_id: Mapped[Optional[str]] = mapped_column(String(50))
    seo_default_author: Mapped[Optional[str]] = mapped_column(String(200))
    seo_social_profiles: Mapped[Optional[dict]] = mapped_column(JSON, default=list)  # URLs de perfiles sociales

    # --- Configuración de publicación ---
    frecuencia_publicacion: Mapped[str] = mapped_column(
        String(20), default="semanal"
    )  # semanal, quincenal, mensual
    auto_publish: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_publish_delay_hours: Mapped[int] = mapped_column(Integer, default=24)
    prompt_industria: Mapped[Optional[str]] = mapped_column(
        String(100), default="general"
    )  # Referencia al archivo de prompts

    # --- Relaciones ---
    # blog_posts = relationship("BlogPost", back_populates="client")
    # social_posts = relationship("SocialPost", back_populates="client")
    # ai_usages = relationship("AIUsage", back_populates="client")
    calendar_entries = relationship("CalendarEntry", back_populates="client", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Client(id={self.id}, nombre='{self.nombre}', plan='{self.plan}')>"

    @property
    def redes_activas(self) -> list[str]:
        """Retorna lista de redes sociales con token configurado."""
        redes = []
        if self.facebook_token_encrypted:
            redes.append("facebook")
        if self.instagram_token_encrypted:
            redes.append("instagram")
        if self.linkedin_token_encrypted:
            redes.append("linkedin")
        if self.twitter_token_encrypted:
            redes.append("twitter")
        if self.pinterest_token_encrypted:
            redes.append("pinterest")
        if self.google_business_token_encrypted:
            redes.append("google_business")
        return redes
