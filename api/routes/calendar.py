"""
BlogEngine - API de Calendario Editorial.
TODO: Implementar planificación editorial con IA.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def ver_calendario(client_id: int = None):
    """Ver calendario editorial (global o por cliente)."""
    # TODO: Implementar
    return {"status": "pendiente", "mensaje": "Calendario editorial en desarrollo"}


@router.post("/generate")
async def generar_calendario(client_id: int, mes: int, anio: int):
    """Genera calendario editorial mensual con IA para un cliente."""
    # TODO: Usar AIRouter para generar temas del mes
    return {"status": "pendiente", "mensaje": "Generación de calendario en desarrollo"}
