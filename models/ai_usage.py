"""
BlogEngine - Modelo de AIUsage.
Tracking de cada llamada a proveedores de IA para control de costos.
"""
from typing import Optional
from sqlalchemy import String, Integer, Text, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class AIUsage(Base, TimestampMixin):
    """Registro de cada llamada a un proveedor de IA."""
    __tablename__ = "ai_usages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)

    # --- Proveedor y modelo ---
    proveedor: Mapped[str] = mapped_column(String(50), nullable=False)  # deepseek, claude
    modelo: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # --- Tipo de tarea ---
    tipo_tarea: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # generacion_articulo, revision_editorial, copies_redes, etc.
    
    # --- Tokens y costo ---
    tokens_input: Mapped[int] = mapped_column(Integer, default=0)
    tokens_output: Mapped[int] = mapped_column(Integer, default=0)
    tokens_total: Mapped[int] = mapped_column(Integer, default=0)
    costo_usd: Mapped[float] = mapped_column(Float, default=0.0)
    cache_hit: Mapped[bool] = mapped_column(default=False)  # DeepSeek cache hit

    # --- Referencia ---
    blog_post_id: Mapped[Optional[int]] = mapped_column(ForeignKey("blog_posts.id"))
    social_post_id: Mapped[Optional[int]] = mapped_column(ForeignKey("social_posts.id"))

    # --- Debug ---
    prompt_preview: Mapped[Optional[str]] = mapped_column(Text)  # Primeros 500 chars del prompt
    exito: Mapped[bool] = mapped_column(default=True)
    error_mensaje: Mapped[Optional[str]] = mapped_column(Text)

    def __repr__(self) -> str:
        return (
            f"<AIUsage(proveedor='{self.proveedor}', tarea='{self.tipo_tarea}', "
            f"costo=${self.costo_usd:.4f})>"
        )
