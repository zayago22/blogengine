"""
BlogEngine - Clase base para proveedores de IA.
Todos los proveedores deben implementar esta interfaz.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class AIResponse:
    """Respuesta estandarizada de cualquier proveedor de IA."""
    contenido: str                  # Texto generado
    tokens_input: int = 0
    tokens_output: int = 0
    costo_usd: float = 0.0
    modelo: str = ""
    proveedor: str = ""
    cache_hit: bool = False
    exito: bool = True
    error: Optional[str] = None

    @property
    def tokens_total(self) -> int:
        return self.tokens_input + self.tokens_output


class AIProvider(ABC):
    """
    Clase base abstracta para proveedores de IA.
    Todos usan formato similar para facilitar intercambio.
    """

    nombre: str = ""
    proveedor_id: str = ""  # deepseek, claude

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 4000,
        temperature: float = 0.7,
        **kwargs,
    ) -> AIResponse:
        """
        Genera texto con el modelo de IA.
        
        Args:
            prompt: Mensaje del usuario.
            system: Mensaje de sistema (instrucciones).
            max_tokens: Máximo de tokens a generar.
            temperature: Creatividad (0.0 - 1.0).
        
        Returns:
            AIResponse con el contenido generado y métricas.
        """
        pass

    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estima el costo en USD para una cantidad de tokens."""
        pass

    def _truncate_for_preview(self, text: str, max_length: int = 500) -> str:
        """Trunca texto para preview en logs/BD."""
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."
