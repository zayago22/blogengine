"""
BlogEngine - Endpoint de prueba para proveedores de IA.
ETAPA 2 — Criterio de aceptación.

Permite verificar que DeepSeek y Claude responden correctamente
y que los costos se registran en ai_usages.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.ai_router import get_ai_router
from core.cost_tracker import CostTracker
from models.base import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# SCHEMAS
# =============================================================================

class TestAIRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Prompt a enviar al LLM")
    provider: str = Field(
        default="deepseek",
        description="Proveedor: 'deepseek' | 'claude'",
    )
    model: str = Field(
        default="",
        description="Modelo: 'deepseek-chat', 'haiku', 'sonnet', 'opus'. Vacío = default.",
    )
    system: str = Field(default="", description="Prompt de sistema (opcional)")
    max_tokens: int = Field(default=300, ge=10, le=4096)
    client_id: Optional[int] = Field(
        default=1,
        description="ID de cliente para registrar costo (usa 1 para tests)",
    )


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/ai")
async def test_ai_provider(
    body: TestAIRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Prueba un proveedor de IA y registra el costo en BD.

    Ejemplos de uso:
    - `{"prompt": "Hola mundo"}` → DeepSeek (default)
    - `{"prompt": "Hola", "provider": "claude", "model": "haiku"}`
    - `{"prompt": "Hola", "provider": "claude", "model": "sonnet"}`
    """
    ai = get_ai_router()

    # Default de modelo según proveedor
    model = body.model
    if not model:
        model = "deepseek-chat" if body.provider == "deepseek" else "haiku"

    logger.info(f"[TestAI] provider={body.provider} model={model} client_id={body.client_id}")

    response = await ai.generate_direct(
        provider_id=body.provider,
        model=model,
        prompt=body.prompt,
        system=body.system,
        max_tokens=body.max_tokens,
    )

    # Registrar costo en BD
    costo_guardado = False
    if body.client_id and response.exito:
        try:
            tracker = CostTracker(db)
            await tracker.registrar(
                client_id=body.client_id,
                tipo_tarea="test",
                response=response,
                prompt_preview=body.prompt,
            )
            await db.commit()
            costo_guardado = True
        except Exception as e:
            logger.warning(f"[TestAI] No se pudo guardar costo: {e}")

    return {
        "exito": response.exito,
        "proveedor": response.proveedor,
        "modelo": response.modelo,
        "respuesta": response.contenido,
        "tokens": {
            "input": response.tokens_input,
            "output": response.tokens_output,
            "total": response.tokens_total,
        },
        "costo_usd": response.costo_usd,
        "cache_hit": response.cache_hit,
        "costo_guardado_en_bd": costo_guardado,
        "error": response.error,
    }


@router.get("/ai/health")
async def health_check_providers():
    """
    Verifica que las API keys están configuradas (sin gastar tokens).
    """
    from config import get_settings
    s = get_settings()

    deepseek_ok = bool(getattr(s, "deepseek_api_key", ""))
    claude_ok   = bool(getattr(s, "anthropic_api_key", ""))

    return {
        "deepseek": {
            "api_key_configurada": deepseek_ok,
            "status": "listo" if deepseek_ok else "falta DEEPSEEK_API_KEY en .env",
        },
        "claude": {
            "api_key_configurada": claude_ok,
            "status": "listo" if claude_ok else "falta ANTHROPIC_API_KEY en .env",
        },
    }


@router.get("/ai/costos")
async def ver_costos_cliente(
    client_id: int = 1,
    db: AsyncSession = Depends(get_db),
):
    """Ver costos acumulados del mes para un cliente."""
    tracker = CostTracker(db)
    total = await tracker.costo_por_cliente(client_id)
    desglose = await tracker.resumen_por_proveedor()
    return {
        "client_id": client_id,
        "costo_total_usd": round(total, 6),
        "desglose_por_proveedor": desglose,
    }
