"""
BlogEngine - API de Analytics.
Métricas de contenido, costos de IA y rendimiento.
"""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import get_db
from core.cost_tracker import CostTracker

router = APIRouter()


@router.get("/costs")
async def costos_ia(
    client_id: Optional[int] = None,
    mes: Optional[int] = None,
    anio: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Consulta costos de IA por cliente o de toda la agencia."""
    tracker = CostTracker(db)
    
    if client_id:
        costo = await tracker.costo_por_cliente(client_id, mes, anio)
        return {"client_id": client_id, "costo_usd": costo}
    else:
        costo = await tracker.costo_total_agencia(mes, anio)
        resumen = await tracker.resumen_por_proveedor(mes, anio)
        return {"costo_total_usd": costo, "por_proveedor": resumen}


@router.get("/dashboard")
async def dashboard():
    """Dashboard general de la agencia."""
    # TODO: Implementar métricas agregadas
    return {"status": "pendiente", "mensaje": "Dashboard en desarrollo"}
