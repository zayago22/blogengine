"""
BlogEngine - Cost Tracker.
Registra cada llamada a proveedores de IA en la base de datos.
Permite consultar costos por cliente, proveedor, periodo, etc.
"""
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.ai_providers.base import AIResponse
from models.ai_usage import AIUsage

logger = logging.getLogger(__name__)


class CostTracker:
    """
    Registra y consulta costos de uso de IA.
    
    Uso:
        tracker = CostTracker(db_session)
        await tracker.registrar(
            client_id=1,
            tipo_tarea="generacion_articulo",
            response=ai_response,
            blog_post_id=42
        )
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def registrar(
        self,
        client_id: int,
        tipo_tarea: str,
        response: AIResponse,
        blog_post_id: Optional[int] = None,
        social_post_id: Optional[int] = None,
        prompt_preview: Optional[str] = None,
    ) -> AIUsage:
        """
        Registra una llamada a IA en la base de datos.
        
        Args:
            client_id: ID del cliente.
            tipo_tarea: Tipo de tarea realizada.
            response: Respuesta del proveedor de IA.
            blog_post_id: ID del blog post relacionado (opcional).
            social_post_id: ID del social post relacionado (opcional).
            prompt_preview: Preview del prompt usado (opcional).
        """
        usage = AIUsage(
            client_id=client_id,
            proveedor=response.proveedor,
            modelo=response.modelo,
            tipo_tarea=tipo_tarea,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            tokens_total=response.tokens_total,
            costo_usd=response.costo_usd,
            cache_hit=response.cache_hit,
            blog_post_id=blog_post_id,
            social_post_id=social_post_id,
            prompt_preview=prompt_preview[:500] if prompt_preview else None,
            exito=response.exito,
            error_mensaje=response.error,
        )

        self.db.add(usage)
        await self.db.flush()

        logger.info(
            f"[CostTracker] Cliente #{client_id} | {response.proveedor}/{response.modelo} | "
            f"{tipo_tarea} | ${response.costo_usd:.4f}"
        )

        return usage

    async def costo_por_cliente(self, client_id: int, mes: int = None, anio: int = None) -> float:
        """Retorna costo total de IA para un cliente, opcionalmente filtrado por mes/año."""
        query = select(func.sum(AIUsage.costo_usd)).where(
            AIUsage.client_id == client_id,
            AIUsage.exito == True,
        )

        if mes and anio:
            query = query.where(
                func.extract("month", AIUsage.created_at) == mes,
                func.extract("year", AIUsage.created_at) == anio,
            )

        result = await self.db.execute(query)
        total = result.scalar()
        return total or 0.0

    async def costo_total_agencia(self, mes: int = None, anio: int = None) -> float:
        """Retorna costo total de IA de toda la agencia."""
        query = select(func.sum(AIUsage.costo_usd)).where(AIUsage.exito == True)

        if mes and anio:
            query = query.where(
                func.extract("month", AIUsage.created_at) == mes,
                func.extract("year", AIUsage.created_at) == anio,
            )

        result = await self.db.execute(query)
        total = result.scalar()
        return total or 0.0

    async def resumen_por_proveedor(self, mes: int = None, anio: int = None) -> list[dict]:
        """Retorna resumen de costos agrupado por proveedor."""
        query = (
            select(
                AIUsage.proveedor,
                func.count(AIUsage.id).label("llamadas"),
                func.sum(AIUsage.tokens_total).label("tokens"),
                func.sum(AIUsage.costo_usd).label("costo"),
            )
            .where(AIUsage.exito == True)
            .group_by(AIUsage.proveedor)
        )

        if mes and anio:
            query = query.where(
                func.extract("month", AIUsage.created_at) == mes,
                func.extract("year", AIUsage.created_at) == anio,
            )

        result = await self.db.execute(query)
        rows = result.all()
        
        return [
            {
                "proveedor": row.proveedor,
                "llamadas": row.llamadas,
                "tokens": row.tokens or 0,
                "costo_usd": round(row.costo or 0, 4),
            }
            for row in rows
        ]
