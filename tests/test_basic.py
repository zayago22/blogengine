"""
BlogEngine - Tests básicos.
Verificar que la aplicación arranca y los modelos funcionan.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app


@pytest.mark.asyncio
async def test_root():
    """Verificar endpoint raíz."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "BlogEngine"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health():
    """Verificar health check."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ai_response_dataclass():
    """Verificar que AIResponse funciona correctamente."""
    from core.ai_providers.base import AIResponse

    response = AIResponse(
        contenido="Hola mundo",
        tokens_input=100,
        tokens_output=50,
        costo_usd=0.001,
        modelo="deepseek-chat",
        proveedor="deepseek",
    )
    assert response.tokens_total == 150
    assert response.exito is True
    assert response.contenido == "Hola mundo"


def test_cost_estimation_deepseek():
    """Verificar cálculo de costos DeepSeek."""
    from core.ai_providers.deepseek import DeepSeekProvider

    provider = DeepSeekProvider.__new__(DeepSeekProvider)
    provider.PRECIO_INPUT = 0.28
    provider.PRECIO_INPUT_CACHE = 0.028
    provider.PRECIO_OUTPUT = 0.42

    # 1M tokens input + 1M tokens output sin cache
    costo = provider._calcular_costo(1_000_000, 1_000_000, cache_hit=False)
    assert abs(costo - 0.70) < 0.01  # $0.28 + $0.42

    # Con cache hit
    costo_cache = provider._calcular_costo(1_000_000, 1_000_000, cache_hit=True)
    assert costo_cache < costo  # Cache debe ser más barato


def test_cost_estimation_claude():
    """Verificar cálculo de costos Claude."""
    from core.ai_providers.claude import ClaudeProvider

    provider = ClaudeProvider.__new__(ClaudeProvider)
    provider.model = "claude-haiku-4-5-20251001"
    provider.PRECIOS = ClaudeProvider.PRECIOS

    costo = provider._calcular_costo(1_000_000, 1_000_000)
    assert abs(costo - 6.00) < 0.01  # $1 + $5
