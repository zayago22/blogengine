"""
BlogEngine - Modelo de Social Post.
Cada publicación distribuida a una red social.
"""
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Integer, Text, JSON, DateTime, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class SocialPost(Base, TimestampMixin):
    """Publicación distribuida a una red social específica."""
    __tablename__ = "social_posts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    blog_post_id: Mapped[int] = mapped_column(ForeignKey("blog_posts.id"), nullable=False, index=True)

    # --- Plataforma ---
    plataforma: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # facebook, instagram, linkedin, twitter, pinterest, google_business
    tipo_contenido: Mapped[str] = mapped_column(
        String(50), default="post"
    )  # post, carrusel, hilo, pin, story

    # --- Contenido adaptado ---
    texto: Mapped[Optional[str]] = mapped_column(Text)
    hashtags: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    media_urls: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    link_url: Mapped[Optional[str]] = mapped_column(String(500))

    # --- Estado ---
    estado: Mapped[str] = mapped_column(
        String(30), default="pendiente"
    )  # pendiente, programado, publicado, fallido
    fecha_programada: Mapped[Optional[datetime]] = mapped_column(DateTime)
    fecha_publicado: Mapped[Optional[datetime]] = mapped_column(DateTime)
    post_id_plataforma: Mapped[Optional[str]] = mapped_column(String(200))  # ID del post en la red
    url_publicado: Mapped[Optional[str]] = mapped_column(String(500))
    error_mensaje: Mapped[Optional[str]] = mapped_column(Text)
    intentos: Mapped[int] = mapped_column(Integer, default=0)

    # --- Métricas ---
    alcance: Mapped[int] = mapped_column(Integer, default=0)
    impresiones: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comentarios: Mapped[int] = mapped_column(Integer, default=0)
    compartidos: Mapped[int] = mapped_column(Integer, default=0)
    clics: Mapped[int] = mapped_column(Integer, default=0)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # --- Costo IA ---
    costo_ia_usd: Mapped[float] = mapped_column(Float, default=0.0)

    def __repr__(self) -> str:
        return f"<SocialPost(id={self.id}, plataforma='{self.plataforma}', estado='{self.estado}')>"
