"""
BlogEngine - API de Webhooks.
Recibe eventos de plataformas externas.
"""
from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/stripe")
async def stripe_webhook(request: Request):
    """Webhook de Stripe para eventos de pago."""
    # TODO: Verificar firma y procesar eventos
    return {"status": "pendiente"}


@router.post("/meta")
async def meta_webhook(request: Request):
    """Webhook de Meta (Facebook/Instagram) para eventos."""
    # TODO: Procesar notificaciones de Meta
    return {"status": "pendiente"}
