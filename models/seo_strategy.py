"""
BlogEngine - Modelos de estrategia SEO.
Toda la inteligencia SEO del cliente vive aquí.
"""
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Integer, Text, JSON, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class MoneyPage(Base, TimestampMixin):
    """
    Página de dinero del cliente.
    Son las URLs donde el cliente CONVIERTE (vende, genera leads, agenda citas).
    CADA artículo del blog debe enviar link juice a estas páginas.
    """
    __tablename__ = "money_pages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)

    url: Mapped[str] = mapped_column(String(500), nullable=False)
    titulo: Mapped[str] = mapped_column(String(300), nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), default="servicio")  # servicio, producto, contacto, landing, whatsapp
    keywords_target: Mapped[Optional[dict]] = mapped_column(JSON, default=list)  # Keywords que esta página debe rankear
    anchor_texts: Mapped[Optional[dict]] = mapped_column(JSON, default=list)  # Textos ancla variados para links
    prioridad: Mapped[int] = mapped_column(Integer, default=1)  # 1-5, mayor = más importante
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class TopicCluster(Base, TimestampMixin):
    """
    Cluster temático (silo de contenido).
    Agrupa keywords relacionadas bajo un tema paraguas.
    
    Estructura:
      Pillar Page → artículo largo y completo sobre el tema general
        ├── Cluster Article 1 → keyword long-tail específica
        ├── Cluster Article 2 → keyword long-tail específica
        └── ...
    
    Todos interlinkeados entre sí → autoridad temática para Google.
    """
    __tablename__ = "topic_clusters"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)

    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    pillar_keyword: Mapped[str] = mapped_column(String(200), nullable=False)
    pillar_titulo_sugerido: Mapped[Optional[str]] = mapped_column(String(300))
    pillar_blog_post_id: Mapped[Optional[int]] = mapped_column(ForeignKey("blog_posts.id"))  # Cuando se cree
    money_pages_ids: Mapped[Optional[dict]] = mapped_column(JSON, default=list)  # IDs de money pages relacionadas
    estado: Mapped[str] = mapped_column(String(30), default="planificado")  # planificado, en_progreso, completado


class SEOKeyword(Base, TimestampMixin):
    """
    Keyword individual a atacar.
    Cada keyword pertenece a un cluster y eventualmente se convierte en un artículo.
    """
    __tablename__ = "seo_keywords"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    cluster_id: Mapped[Optional[int]] = mapped_column(ForeignKey("topic_clusters.id"), index=True)

    keyword: Mapped[str] = mapped_column(String(300), nullable=False)
    keywords_secundarias: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    intencion: Mapped[str] = mapped_column(String(30), default="informacional")  # informacional, transaccional, navegacional
    dificultad_estimada: Mapped[str] = mapped_column(String(20), default="media")  # baja, media, alta
    volumen_estimado: Mapped[str] = mapped_column(String(20), default="medio")  # bajo, medio, alto
    titulo_sugerido: Mapped[Optional[str]] = mapped_column(String(300))
    prioridad: Mapped[int] = mapped_column(Integer, default=3)  # 1-5
    es_pillar: Mapped[bool] = mapped_column(Boolean, default=False)

    # Estado
    estado: Mapped[str] = mapped_column(
        String(30), default="pendiente"
    )  # pendiente, en_progreso, publicado, descartado
    blog_post_id: Mapped[Optional[int]] = mapped_column(ForeignKey("blog_posts.id"))  # Cuando se genere el artículo

    # Tracking de posición
    posicion_actual: Mapped[Optional[int]] = mapped_column(Integer)  # Posición en Google (1-100)
    posicion_anterior: Mapped[Optional[int]] = mapped_column(Integer)
    ultima_verificacion: Mapped[Optional[datetime]] = mapped_column(DateTime)


class SEOAuditLog(Base, TimestampMixin):
    """
    Registro de auditoría SEO de cada artículo.
    Guarda la puntuación y problemas encontrados ANTES de publicar.
    """
    __tablename__ = "seo_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    blog_post_id: Mapped[int] = mapped_column(ForeignKey("blog_posts.id"), nullable=False, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)

    puntuacion: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    keyword_principal: Mapped[str] = mapped_column(String(200))
    checks: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    problemas_criticos: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    sugerencias: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    stats: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    # ¿Pasó la auditoría?
    aprobado: Mapped[bool] = mapped_column(Boolean, default=False)
    revision_automatica: Mapped[bool] = mapped_column(Boolean, default=False)  # Si se mandó a corregir con IA
