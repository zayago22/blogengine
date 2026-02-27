"""
BlogEngine - Modelo de Blog Post.
Representa un artículo generado para un cliente.
"""
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Integer, Text, JSON, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class BlogPost(Base, TimestampMixin):
    """Modelo de artículo de blog."""
    __tablename__ = "blog_posts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)

    # --- Contenido ---
    titulo: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(500), nullable=False)
    meta_description: Mapped[Optional[str]] = mapped_column(String(320))
    contenido_html: Mapped[Optional[str]] = mapped_column(Text)
    contenido_markdown: Mapped[Optional[str]] = mapped_column(Text)
    extracto: Mapped[Optional[str]] = mapped_column(Text)
    
    # --- SEO ---
    keyword_principal: Mapped[Optional[str]] = mapped_column(String(200))
    keywords_secundarias: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    internal_links: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    
    # --- Media ---
    imagen_destacada_url: Mapped[Optional[str]] = mapped_column(String(500))
    imagen_destacada_alt: Mapped[Optional[str]] = mapped_column(String(300))
    imagenes_adicionales: Mapped[Optional[dict]] = mapped_column(JSON, default=list)

    # --- Estado y publicación ---
    estado: Mapped[str] = mapped_column(
        String(30), default="borrador"
    )  # borrador, en_revision, aprobado, publicado, fallido, rechazado
    fecha_programada: Mapped[Optional[datetime]] = mapped_column(DateTime)
    fecha_publicado: Mapped[Optional[datetime]] = mapped_column(DateTime)
    url_publicado: Mapped[Optional[str]] = mapped_column(String(500))
    cms_post_id: Mapped[Optional[str]] = mapped_column(String(100))  # ID en el CMS del cliente
    auto_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # --- IA y generación ---
    proveedor_generacion: Mapped[Optional[str]] = mapped_column(String(50))  # deepseek, claude
    modelo_generacion: Mapped[Optional[str]] = mapped_column(String(100))
    proveedor_revision: Mapped[Optional[str]] = mapped_column(String(50))
    modelo_revision: Mapped[Optional[str]] = mapped_column(String(100))
    prompt_usado: Mapped[Optional[str]] = mapped_column(Text)
    tokens_input_total: Mapped[int] = mapped_column(Integer, default=0)
    tokens_output_total: Mapped[int] = mapped_column(Integer, default=0)
    costo_ia_total_usd: Mapped[float] = mapped_column(Float, default=0.0)

    # --- Métricas (se actualizan después) ---
    visitas: Mapped[int] = mapped_column(Integer, default=0)
    tiempo_en_pagina_segundos: Mapped[int] = mapped_column(Integer, default=0)
    posicion_google: Mapped[Optional[int]] = mapped_column(Integer)
    
    # --- Categorías y tags ---
    categorias: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    tags: Mapped[Optional[dict]] = mapped_column(JSON, default=list)

    # --- Distribución social ---
    distribuido_a: Mapped[Optional[dict]] = mapped_column(JSON, default=list)  # Lista de redes donde se distribuyó
    distribucion_completada: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"<BlogPost(id={self.id}, titulo='{self.titulo[:50]}', estado='{self.estado}')>"
