"""
BlogEngine - Proveedor DeepSeek V3.2.
Usa formato compatible con OpenAI para generación masiva de contenido a bajo costo.

Precios (por 1M tokens):
  - Input (cache miss): $0.28
  - Input (cache hit):  $0.028
  - Output:             $0.42
"""
import logging
from typing import Optional
from openai import AsyncOpenAI

from core.ai_providers.base import AIProvider, AIResponse
from config import get_settings

logger = logging.getLogger(__name__)


class DeepSeekProvider(AIProvider):
    """
    DeepSeek V3.2 — Para generación masiva de contenido a bajo costo.
    
    Usa la librería openai ya que DeepSeek es API-compatible con OpenAI.
    Solo cambiamos base_url y api_key.
    """

    nombre = "DeepSeek V3.2"
    proveedor_id = "deepseek"

    # Precios por 1M tokens (USD)
    PRECIO_INPUT = 0.28
    PRECIO_INPUT_CACHE = 0.028
    PRECIO_OUTPUT = 0.42

    def __init__(self, model: str = "deepseek-chat"):
        """
        Args:
            model: Modelo a usar. 'deepseek-chat' (no-razonamiento) 
                   o 'deepseek-reasoner' (razonamiento).
        """
        settings = get_settings()
        self.model = model
        self.client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )

    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 4000,
        temperature: float = 0.7,
        **kwargs,
    ) -> AIResponse:
        """Genera texto usando DeepSeek V3.2."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs,
            )

            # Extraer métricas de uso
            tokens_input = response.usage.prompt_tokens if response.usage else 0
            tokens_output = response.usage.completion_tokens if response.usage else 0
            
            # Detectar cache hit si está disponible en la respuesta
            cache_hit = False
            if hasattr(response.usage, "prompt_cache_hit_tokens"):
                cache_hit = response.usage.prompt_cache_hit_tokens > 0

            # Calcular costo
            costo = self._calcular_costo(tokens_input, tokens_output, cache_hit)

            contenido = response.choices[0].message.content or ""

            logger.info(
                f"[DeepSeek] Generado: {tokens_input} in + {tokens_output} out = "
                f"${costo:.4f} USD (cache: {cache_hit})"
            )

            return AIResponse(
                contenido=contenido,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                costo_usd=costo,
                modelo=self.model,
                proveedor=self.proveedor_id,
                cache_hit=cache_hit,
                exito=True,
            )

        except Exception as e:
            logger.error(f"[DeepSeek] Error: {e}")
            return AIResponse(
                contenido="",
                proveedor=self.proveedor_id,
                modelo=self.model,
                exito=False,
                error=str(e),
            )

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estima costo sin cache."""
        return self._calcular_costo(input_tokens, output_tokens, cache_hit=False)

    def _calcular_costo(
        self, input_tokens: int, output_tokens: int, cache_hit: bool = False
    ) -> float:
        """Calcula costo real en USD."""
        precio_input = self.PRECIO_INPUT_CACHE if cache_hit else self.PRECIO_INPUT
        costo_input = (input_tokens / 1_000_000) * precio_input
        costo_output = (output_tokens / 1_000_000) * self.PRECIO_OUTPUT
        return round(costo_input + costo_output, 6)
