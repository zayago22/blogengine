"""
BlogEngine - AI Router.
Enruta cada tarea al proveedor de IA más adecuado según:
  - Tipo de tarea
  - Plan del cliente
  - Configuración en config.yaml
  - Fallback automático si un proveedor falla
"""
import logging
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from core.ai_providers.base import AIProvider, AIResponse
from core.ai_providers.deepseek import DeepSeekProvider
from core.ai_providers.claude import ClaudeProvider
from config import get_config

logger = logging.getLogger(__name__)


class AIRouter:
    """
    Enrutador inteligente de tareas de IA.
    
    Nunca llames directamente a DeepSeek o Claude.
    Siempre usa el router para que:
    1. Se seleccione el proveedor correcto según tarea + plan
    2. Se aplique fallback automático si falla
    3. Se trackeen costos centralizadamente
    
    Uso:
        router = AIRouter()
        response = await router.generate(
            task_type="generacion_articulo",
            client_plan="starter",
            prompt="Escribe un artículo sobre...",
            system="Eres un redactor SEO experto..."
        )
    """

    def __init__(self):
        self.config = get_config()
        self.routing_config = self.config.get("ai_routing", {})

        # Cache de proveedores instanciados
        self._providers: dict[str, AIProvider] = {}

    def _get_provider(self, provider_id: str, model: str) -> AIProvider:
        """Obtiene o crea instancia del proveedor."""
        cache_key = f"{provider_id}:{model}"
        
        if cache_key not in self._providers:
            if provider_id == "deepseek":
                self._providers[cache_key] = DeepSeekProvider(model=model)
            elif provider_id == "claude":
                self._providers[cache_key] = ClaudeProvider(model=model)
            else:
                raise ValueError(f"Proveedor desconocido: {provider_id}")
        
        return self._providers[cache_key]

    def _resolve_provider(
        self, task_type: str, client_plan: str
    ) -> Optional[tuple[str, str]]:
        """
        Resuelve qué proveedor y modelo usar para una tarea y plan.
        
        Returns:
            Tupla (provider_id, model) o None si la tarea no está disponible para el plan.
        """
        task_config = self.routing_config.get(task_type, {})
        plan_config = task_config.get(client_plan)

        if plan_config is None:
            logger.warning(
                f"Tarea '{task_type}' no disponible para plan '{client_plan}'"
            )
            return None

        return (plan_config["provider"], plan_config["model"])

    def _get_fallback_provider(self) -> AIProvider:
        """Retorna Claude Haiku como fallback universal."""
        return self._get_provider("claude", "haiku")

    async def generate(
        self,
        task_type: str,
        client_plan: str,
        prompt: str,
        system: str = "",
        max_tokens: int = 4000,
        temperature: float = 0.7,
        use_fallback: bool = True,
        **kwargs,
    ) -> AIResponse:
        """
        Genera contenido enrutando al proveedor correcto.
        
        Args:
            task_type: Tipo de tarea (generacion_articulo, revision_editorial, etc.)
            client_plan: Plan del cliente (free, starter, pro)
            prompt: Mensaje del usuario.
            system: Instrucciones de sistema.
            max_tokens: Máximo de tokens a generar.
            temperature: Creatividad.
            use_fallback: Si True, usa Claude Haiku si el proveedor principal falla.
        
        Returns:
            AIResponse con contenido y métricas de costo.
        
        Raises:
            ValueError: Si la tarea no está disponible para el plan.
        """
        # 1. Resolver proveedor según tarea + plan
        resolved = self._resolve_provider(task_type, client_plan)
        if resolved is None:
            return AIResponse(
                contenido="",
                exito=False,
                error=f"Tarea '{task_type}' no disponible para plan '{client_plan}'",
            )

        provider_id, model = resolved
        provider = self._get_provider(provider_id, model)

        logger.info(
            f"[Router] Tarea: {task_type} | Plan: {client_plan} → "
            f"{provider_id}/{model}"
        )

        # 2. Intentar con proveedor principal
        response = await provider.generate(
            prompt=prompt,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

        # 3. Fallback si falla
        if not response.exito and use_fallback:
            logger.warning(
                f"[Router] {provider_id} falló: {response.error}. "
                f"Usando fallback Claude Haiku..."
            )
            fallback = self._get_fallback_provider()
            response = await fallback.generate(
                prompt=prompt,
                system=system,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            if response.exito:
                logger.info("[Router] Fallback exitoso con Claude Haiku")

        return response

    async def generate_direct(
        self,
        provider_id: str,
        model: str,
        prompt: str,
        system: str = "",
        max_tokens: int = 4000,
        temperature: float = 0.7,
    ) -> AIResponse:
        """
        Genera contenido con un proveedor específico (sin enrutamiento).
        Usar solo cuando se necesita forzar un proveedor concreto.
        """
        provider = self._get_provider(provider_id, model)
        return await provider.generate(
            prompt=prompt,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def is_task_available(self, task_type: str, client_plan: str) -> bool:
        """Verifica si una tarea está disponible para un plan."""
        return self._resolve_provider(task_type, client_plan) is not None

    def get_estimated_cost(
        self, task_type: str, client_plan: str, input_tokens: int, output_tokens: int
    ) -> Optional[float]:
        """Estima costo de una tarea para un plan."""
        resolved = self._resolve_provider(task_type, client_plan)
        if resolved is None:
            return None
        provider_id, model = resolved
        provider = self._get_provider(provider_id, model)
        return provider.estimate_cost(input_tokens, output_tokens)


# Instancia global del router
_router: Optional[AIRouter] = None


def get_ai_router() -> AIRouter:
    """Retorna instancia global del router."""
    global _router
    if _router is None:
        _router = AIRouter()
    return _router
