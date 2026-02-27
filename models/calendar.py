"""
BlogEngine - Modelo CalendarEntry.
Representa una entrada en el calendario de contenido de un cliente.
"""
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Integer, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class CalendarEntry(Base):
    """Entrada del calendario editorial de un cliente."""
    __tablename__ = "calendar_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    keyword_id: Mapped[Optional[int]] = mapped_column(ForeignKey("seo_keywords.id"), nullable=True)

    # --- Contenido planificado ---
    titulo_sugerido: Mapped[str] = mapped_column(String(500), nullable=False)
    keyword_principal: Mapped[str] = mapped_column(String(200), nullable=False)

    # --- Programación ---
    fecha_programada: Mapped[date] = mapped_column(Date, nullable=False)
    semana_del_mes: Mapped[Optional[int]] = mapped_column(Integer)  # 1-4

    # --- Estado y prioridad ---
    prioridad: Mapped[str] = mapped_column(
        String(20), default="media"
    )  # alta, media, baja
    estado: Mapped[str] = mapped_column(
        String(20), default="pendiente"
    )  # pendiente, generando, generado, publicado, cancelado

    # --- Notas adicionales ---
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Timestamp ---
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # --- Relaciones ---
    client = relationship("Client", back_populates="calendar_entries")
    keyword = relationship("SEOKeyword")

    def __repr__(self) -> str:
        return f"<CalendarEntry(id={self.id}, keyword='{self.keyword_principal}', fecha='{self.fecha_programada}', estado='{self.estado}')>"
