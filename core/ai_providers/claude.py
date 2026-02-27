"""
BlogEngine - Proveedor Claude (Anthropic).
Para revisión editorial, contenido premium y análisis SEO.

Precios (por 1M tokens):
  Haiku:  $1 input / $5 output
  Sonnet: $3 input / $15 output
  Opus:   $5 input / $25 output
"""
import logging
from typing import Optional
from anthropic import AsyncAnthropic

from core.ai_providers.base import AIProvider, AIResponse
from config import get_settings

logger = logging.getLogger(__name__)


class ClaudeProvider(AIProvider):
    """
    Claude (Anthropic) — Para revisión editorial, contenido premium y análisis.
    
    Usa la librería oficial de Anthropic.
    """

    nombre = "Claude (Anthropic)"
    proveedor_id = "claude"

    # Precios por 1M tokens (USD)
    PRECIOS = {
        "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
        "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
        "claude-opus-4-6": {"input": 5.00, "output": 25.00},
    }

    # Aliases para facilitar el uso
    MODELOS = {
        "haiku": "claude-haiku-4-5-20251001",
        "sonnet": "claude-sonnet-4-5-20250929",
        "opus": "claude-opus-4-6",
    }

    def __init__(self, model: str = "haiku"):
        """
        Args:
            model: Alias del modelo ('haiku', 'sonnet', 'opus') 
                   o nombre completo del modelo.
        """
        settings = get_settings()
        # Resolver alias a nombre completo
        self.model = self.MODELOS.get(model, model)
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> AIResponse:
        """Genera texto usando Claude."""
        try:
            params = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                params["system"] = system

            response = await self.client.messages.create(**params)

            # Extraer métricas
            tokens_input = response.usage.input_tokens
            tokens_output = response.usage.output_tokens

            # Calcular costo
            costo = self._calcular_costo(tokens_input, tokens_output)

            # Extraer texto de los bloques de contenido
            contenido = ""
            for block in response.content:
                if block.type == "text":
                    contenido += block.text

            logger.info(
                f"[Claude/{self.model}] Generado: {tokens_input} in + "
                f"{tokens_output} out = ${costo:.4f} USD"
            )

            return AIResponse(
                contenido=contenido,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                costo_usd=costo,
                modelo=self.model,
                proveedor=self.proveedor_id,
                exito=True,
            )

        except Exception as e:
            logger.error(f"[Claude] Error: {e}")
            return AIResponse(
                contenido="",
                proveedor=self.proveedor_id,
                modelo=self.model,
                exito=False,
                error=str(e),
            )

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estima costo para el modelo actual."""
        return self._calcular_costo(input_tokens, output_tokens)

    def _calcular_costo(self, input_tokens: int, output_tokens: int) -> float:
        """Calcula costo real en USD."""
        precios = self.PRECIOS.get(self.model, {"input": 3.00, "output": 15.00})
        costo_input = (input_tokens / 1_000_000) * precios["input"]
        costo_output = (output_tokens / 1_000_000) * precios["output"]
        return round(costo_input + costo_output, 6)
