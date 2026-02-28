"""
BlogEngine - Client SEO Strategy Engine.

FILOSOFÍA: Cada artículo existe para POSICIONAR AL CLIENTE en Google.
No es "un blog bonito". Es una máquina de tráfico orgánico.

El blog es un instrumento para:
1. Atraer tráfico orgánico con keywords de cola larga
2. Pasar link juice a las páginas de dinero del cliente (servicios, contacto, productos)
3. Construir autoridad temática (topical authority) en el nicho del cliente
4. Generar leads con CTAs estratégicos

ESTRATEGIA SEO POR ARTÍCULO:
============================
- Cada artículo ataca UNA keyword principal + 3-5 keywords secundarias
- Título optimizado (<60 chars, keyword al inicio)
- Meta description con keyword + CTA (<155 chars)
- H1 = keyword principal (variación natural)
- H2s = keywords secundarias o preguntas del usuario
- Internal links: a otros artículos del blog (distribuir autoridad)
- Money links: 1-2 links estratégicos a páginas de servicio/producto del cliente
- CTA: siempre dirigir al negocio del cliente
- Estructura de silo: artículos agrupados por temática → pillar + cluster
"""
import logging
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# Modelo de estrategia SEO del cliente
# =============================================================================

@dataclass
class MoneyPage:
    """
    Página de dinero del cliente.
    Son las páginas donde el cliente CONVIERTE (vende, genera leads, etc.)
    El blog debe enviar tráfico y link juice a estas páginas.
    """
    url: str                          # https://cliente.com/servicios/renta
    titulo: str                       # "Renta de propiedades"
    keywords_target: list[str]        # ["renta departamento cdmx", "rentar casa"]
    anchor_texts: list[str]           # Textos ancla variados para los links
    tipo: str = "servicio"            # servicio, producto, contacto, landing
    prioridad: int = 1               # 1-5, mayor = más importante


@dataclass
class TopicCluster:
    """
    Cluster temático (silo de contenido).
    
    Estructura:
      Pillar Page (artículo extenso, keyword principal competitiva)
        ├── Cluster Article 1 (keyword long-tail relacionada)
        ├── Cluster Article 2
        ├── Cluster Article 3
        └── ...
    
    Todos los artículos del cluster se enlazan entre sí
    y al pillar page, creando autoridad temática.
    """
    nombre: str                          # "Inversión inmobiliaria"
    pillar_keyword: str                  # "invertir en bienes raíces méxico"
    pillar_slug: str = ""                # slug del pillar page (cuando exista)
    cluster_keywords: list[str] = field(default_factory=list)   # Keywords de artículos satélite
    money_pages: list[str] = field(default_factory=list)        # URLs de páginas de dinero relacionadas


@dataclass
class ClientSEOStrategy:
    """
    Estrategia SEO completa de un cliente.
    Define: qué keywords atacar, cómo estructurar el contenido,
    y hacia dónde enviar el tráfico.
    """
    client_id: int
    
    # Páginas de dinero (donde el cliente convierte)
    money_pages: list[MoneyPage] = field(default_factory=list)
    
    # Clusters temáticos (silos de contenido)
    topic_clusters: list[TopicCluster] = field(default_factory=list)
    
    # Keywords ya atacadas (para no repetir)
    keywords_used: list[str] = field(default_factory=list)
    
    # Configuración de internal linking
    max_internal_links_per_article: int = 3
    max_money_links_per_article: int = 2
    
    # Configuración de CTA
    cta_principal: str = ""
    cta_url: str = ""
    cta_telefono: str = ""
    cta_whatsapp: str = ""


# =============================================================================
# Optimizador On-Page SEO
# =============================================================================

class OnPageSEOOptimizer:
    """
    Verifica y optimiza el SEO on-page de cada artículo ANTES de publicar.
    
    Checklist que aplica:
    ✅ Título: keyword al inicio, <60 chars
    ✅ Meta description: keyword presente, CTA, <155 chars
    ✅ H1: incluye keyword (variación natural)
    ✅ URL/Slug: keyword en slug, corto, sin stop words
    ✅ Primer párrafo: keyword en las primeras 100 palabras
    ✅ H2s: al menos 3, keywords secundarias en algunos
    ✅ Keyword density: 1-2% (natural, no forzado)
    ✅ Internal links: mínimo 2 a otros artículos del blog
    ✅ Money links: 1-2 a páginas de servicio del cliente
    ✅ Imágenes: alt text con keyword
    ✅ Longitud: mínimo 800 palabras
    ✅ Legibilidad: párrafos cortos, oraciones variadas
    """

    @staticmethod
    def audit(
        titulo: str,
        meta_description: str,
        slug: str,
        contenido_html: str,
        keyword_principal: str,
        keywords_secundarias: list[str] = None,
        existing_posts_count: int = None,
    ) -> dict:
        """
        Audita el SEO on-page de un artículo.
        
        Returns:
            {
                "puntuacion": 0-100,
                "checks": [{"check": "...", "passed": bool, "detalle": "..."}],
                "problemas_criticos": ["..."],
                "sugerencias": ["..."],
            }
        """
        import re
        
        checks = []
        problemas = []
        sugerencias = []
        puntos = 0
        keyword = keyword_principal.lower()
        keywords_sec = [k.lower() for k in (keywords_secundarias or [])]
        
        # Limpiar HTML para análisis de texto
        text_content = re.sub(r'<[^>]+>', ' ', contenido_html).lower()
        words = text_content.split()
        word_count = len(words)
        
        # --- 1. TÍTULO (15 puntos) ---
        titulo_lower = titulo.lower()
        titulo_has_keyword = keyword in titulo_lower
        titulo_keyword_first = titulo_lower.startswith(keyword) or titulo_lower.find(keyword) < 20
        titulo_length_ok = len(titulo) <= 60
        
        if titulo_has_keyword and titulo_keyword_first:
            checks.append({"check": "Keyword en título (al inicio)", "passed": True, "detalle": f"'{keyword}' encontrada en posición óptima"})
            puntos += 15
        elif titulo_has_keyword:
            checks.append({"check": "Keyword en título", "passed": True, "detalle": "Presente pero no al inicio"})
            puntos += 10
            sugerencias.append(f"Mover '{keyword}' más al inicio del título")
        else:
            checks.append({"check": "Keyword en título", "passed": False, "detalle": f"'{keyword}' NO encontrada en título"})
            problemas.append(f"❌ Keyword principal '{keyword}' no está en el título")
        
        if titulo_length_ok:
            checks.append({"check": "Largo de título", "passed": True, "detalle": f"{len(titulo)} chars (máx 60)"})
            puntos += 5
        else:
            checks.append({"check": "Largo de título", "passed": False, "detalle": f"{len(titulo)} chars (máx 60)"})
            sugerencias.append(f"Acortar título a menos de 60 caracteres (actual: {len(titulo)})")
        
        # --- 2. META DESCRIPTION (10 puntos) ---
        meta_lower = meta_description.lower()
        meta_has_keyword = keyword in meta_lower
        meta_length_ok = 120 <= len(meta_description) <= 155
        
        if meta_has_keyword:
            checks.append({"check": "Keyword en meta description", "passed": True})
            puntos += 5
        else:
            checks.append({"check": "Keyword en meta description", "passed": False})
            problemas.append("❌ Keyword no está en la meta description")
        
        if meta_length_ok:
            checks.append({"check": "Largo de meta description", "passed": True, "detalle": f"{len(meta_description)} chars"})
            puntos += 5
        else:
            checks.append({"check": "Largo de meta description", "passed": False, "detalle": f"{len(meta_description)} chars (ideal: 120-155)"})
        
        # --- 3. SLUG (5 puntos) ---
        slug_has_keyword = keyword.replace(" ", "-") in slug.lower() or keyword.replace(" ", "") in slug.lower().replace("-", "")
        if slug_has_keyword:
            checks.append({"check": "Keyword en slug", "passed": True})
            puntos += 5
        else:
            checks.append({"check": "Keyword en slug", "passed": False})
            sugerencias.append(f"Incluir keyword en el slug: '{keyword.replace(' ', '-')}'")
        
        # --- 4. PRIMER PÁRRAFO (10 puntos) ---
        first_100_words = " ".join(words[:100])
        if keyword in first_100_words:
            checks.append({"check": "Keyword en primeras 100 palabras", "passed": True})
            puntos += 10
        else:
            checks.append({"check": "Keyword en primeras 100 palabras", "passed": False})
            problemas.append("❌ Keyword no aparece en las primeras 100 palabras")
        
        # --- 5. H2s Y ESTRUCTURA (10 puntos) ---
        h2_matches = re.findall(r'<h2[^>]*>(.*?)</h2>', contenido_html, re.IGNORECASE)
        h2_count = len(h2_matches)
        h2_with_keywords = sum(1 for h2 in h2_matches if any(k in h2.lower() for k in [keyword] + keywords_sec))
        
        if h2_count >= 3:
            checks.append({"check": f"Estructura H2 ({h2_count} secciones)", "passed": True})
            puntos += 5
        else:
            checks.append({"check": f"Estructura H2 ({h2_count} secciones)", "passed": False})
            sugerencias.append("Agregar más secciones H2 (mínimo 3)")
        
        if h2_with_keywords >= 1:
            checks.append({"check": "Keywords en H2s", "passed": True, "detalle": f"{h2_with_keywords} H2s con keywords"})
            puntos += 5
        else:
            checks.append({"check": "Keywords en H2s", "passed": False})
            sugerencias.append("Incluir keywords secundarias en al menos un H2")
        
        # --- 6. KEYWORD DENSITY (10 puntos) ---
        keyword_count = text_content.count(keyword)
        density = (keyword_count / max(word_count, 1)) * 100 if word_count > 0 else 0
        density_ok = 0.5 <= density <= 2.5
        
        if density_ok:
            checks.append({"check": f"Keyword density ({density:.1f}%)", "passed": True})
            puntos += 10
        elif density < 0.5:
            checks.append({"check": f"Keyword density ({density:.1f}%)", "passed": False, "detalle": "Muy baja"})
            sugerencias.append(f"Keyword density muy baja ({density:.1f}%). Usar la keyword más veces de forma natural.")
        else:
            checks.append({"check": f"Keyword density ({density:.1f}%)", "passed": False, "detalle": "Muy alta (riesgo keyword stuffing)"})
            sugerencias.append(f"Keyword density alta ({density:.1f}%). Reducir para evitar penalización.")
        
        # --- 7. INTERNAL LINKS (10 puntos) ---
        # Links internos = relativos (no empiezan con http:// o https://)
        all_hrefs = re.findall(r'<a[^>]+href=["\']([^"\']*)["\']', contenido_html, re.IGNORECASE)
        internal_links = [h for h in all_hrefs if not h.startswith(('http://', 'https://', 'mailto:', 'tel:'))]
        external_links = [h for h in all_hrefs if h.startswith(('http://', 'https://'))]
        internal_count = len(internal_links)
        external_count = len(external_links)
        
        # Si es el primer artículo del cliente, no penalizar por internal links
        # (no hay otros posts a los que enlazar todavía)
        primer_articulo = existing_posts_count is not None and existing_posts_count <= 1

        if internal_count >= 2:
            checks.append({"check": f"Internal links ({internal_count})", "passed": True})
            puntos += 10
        elif internal_count == 1:
            if primer_articulo:
                checks.append({"check": f"Internal links ({internal_count})", "passed": True, "detalle": "Primer artículo — sin penalización"})
                puntos += 10
            else:
                checks.append({"check": f"Internal links ({internal_count})", "passed": False, "detalle": "Mínimo 2"})
                puntos += 5
                sugerencias.append("Agregar al menos 1 internal link más a otros artículos del blog.")
        else:
            if primer_articulo:
                checks.append({"check": "Internal links (0)", "passed": True, "detalle": "Primer artículo — sin penalización"})
                puntos += 10
            else:
                checks.append({"check": "Internal links (0)", "passed": False})
                problemas.append("❌ Sin internal links. Agregar mínimo 2 links a otros artículos del blog.")
        
        # --- 8. LONGITUD (10 puntos) ---
        if word_count >= 800:
            checks.append({"check": f"Longitud ({word_count} palabras)", "passed": True})
            puntos += 10
        elif word_count >= 500:
            checks.append({"check": f"Longitud ({word_count} palabras)", "passed": True, "detalle": "Aceptable pero corto"})
            puntos += 5
            sugerencias.append(f"Artículo corto ({word_count} palabras). Ideal: 800-1500.")
        else:
            checks.append({"check": f"Longitud ({word_count} palabras)", "passed": False})
            problemas.append(f"❌ Artículo muy corto ({word_count} palabras). Mínimo 800.")
        
        # --- 9. IMÁGENES CON ALT (5 puntos) ---
        img_tags = re.findall(r'<img[^>]*>', contenido_html)
        img_with_alt = sum(1 for img in img_tags if 'alt=' in img and 'alt=""' not in img)
        
        if img_tags and img_with_alt == len(img_tags):
            checks.append({"check": "Imágenes con alt text", "passed": True})
            puntos += 5
        elif not img_tags:
            checks.append({"check": "Imágenes", "passed": False, "detalle": "Sin imágenes"})
            sugerencias.append("Agregar al menos 1 imagen con alt text que incluya la keyword")
        else:
            checks.append({"check": f"Alt text en imágenes ({img_with_alt}/{len(img_tags)})", "passed": False})
        
        # --- 10. KEYWORDS SECUNDARIAS (10 puntos) ---
        sec_found = sum(1 for k in keywords_sec if k in text_content)
        if keywords_sec and sec_found >= len(keywords_sec) * 0.5:
            checks.append({"check": f"Keywords secundarias ({sec_found}/{len(keywords_sec)})", "passed": True})
            puntos += 10
        elif keywords_sec:
            checks.append({"check": f"Keywords secundarias ({sec_found}/{len(keywords_sec)})", "passed": False})
            missing = [k for k in keywords_sec if k not in text_content]
            sugerencias.append(f"Keywords secundarias faltantes: {', '.join(missing[:3])}")
        
        # --- 8b. MONEY LINKS check (10 puntos) ---
        if external_count >= 1:
            checks.append({"check": f"Money/external links ({external_count})", "passed": True})
            puntos += 10
        else:
            checks.append({"check": "Money links (0)", "passed": False})
            problemas.append("❌ Sin money links. Agregar al menos 1 link al sitio del cliente.")

        return {
            "puntuacion": min(puntos, 100),
            "checks": checks,
            "problemas_criticos": problemas,
            "sugerencias": sugerencias,
            "stats": {
                "palabras": word_count,
                "h2s": h2_count,
                "links_internos": internal_count,
                "links_externos": external_count,
                "keyword_density": round(density, 2),
                "keyword_count": keyword_count,
            },
        }


# =============================================================================
# Prompt Builder SEO-First
# =============================================================================

class SEOPromptBuilder:
    """
    Construye prompts de generación de artículos con SEO como prioridad.
    
    La diferencia con un prompt normal:
    - Especifica keyword principal y dónde debe ir
    - Define estructura exacta de H2s con keywords secundarias
    - Incluye instrucciones de money links al sitio del cliente
    - Pide internal links a artículos existentes
    - Controla keyword density
    - Exige primer párrafo con keyword
    """

    @staticmethod
    def build_generation_prompt(
        tema: str,
        keyword_principal: str,
        keywords_secundarias: list[str],
        client_name: str,
        client_industry: str,
        client_tone: str,
        client_url: str,
        money_pages: list[MoneyPage] = None,
        existing_posts: list[dict] = None,
        language: str = "es",
        target_words: int = 1200,
    ) -> tuple[str, str]:
        """
        Construye system prompt y user prompt optimizados para SEO.
        
        Returns:
            (system_prompt, user_prompt)
        """
        money_pages = money_pages or []
        existing_posts = existing_posts or []
        
        # --- System Prompt ---
        system = f"""Eres un redactor SEO experto. Tu ÚNICO objetivo es escribir un artículo 
que POSICIONE EN GOOGLE para la keyword "{keyword_principal}".

REGLAS SEO OBLIGATORIAS — NO NEGOCIABLES:
==========================================

1. KEYWORD PRINCIPAL: "{keyword_principal}"
   - DEBE aparecer en el título (primeras 5 palabras idealmente)
   - DEBE aparecer en el primer párrafo (primeras 50 palabras)
   - DEBE aparecer en al menos 1 H2
   - DEBE aparecer 4-8 veces en total (density ~1-2%)
   - Usar variaciones naturales también

2. KEYWORDS SECUNDARIAS: {', '.join(f'"{k}"' for k in keywords_secundarias) if keywords_secundarias else 'ninguna'}
   - Cada una debe aparecer al menos 1 vez en el artículo
   - Idealmente en un H2 o H3

3. ESTRUCTURA:
   - Título H1: máximo 60 caracteres, keyword al inicio
   - Mínimo 4 secciones con H2
   - Al menos 1 H3 dentro de algún H2
   - Párrafos cortos (3-4 oraciones máximo)
   - Longitud total: {target_words} palabras aproximadamente

4. PRIMER PÁRRAFO:
   - Hook que enganche al lector
   - Keyword principal en las primeras 2 oraciones
   - Debe responder la intención de búsqueda del usuario

5. ÚLTIMO PÁRRAFO:
   - Resumen de los puntos clave
   - CTA claro dirigido al negocio del cliente

CLIENTE: {client_name}
INDUSTRIA: {client_industry}
TONO: {client_tone}
SITIO WEB: {client_url}
IDIOMA: {language}

IMPORTANTE: El artículo NO debe sonar robótico ni genérico. 
Debe ser útil, con datos concretos y ejemplos reales.
Debe sonar como si lo escribió un experto humano del sector."""

        # --- User Prompt ---
        user_parts = [f"""Escribe un artículo de blog SEO-optimizado.

TEMA: {tema}
KEYWORD PRINCIPAL: {keyword_principal}
KEYWORDS SECUNDARIAS: {', '.join(keywords_secundarias) if keywords_secundarias else 'ninguna'}
"""]

        # Money links
        if money_pages:
            user_parts.append("\nLINKS AL SITIO DEL CLIENTE (incluir de forma natural en el artículo):")
            for mp in money_pages[:2]:  # Máximo 2 money links por artículo
                anchors = ' o '.join(f'"{a}"' for a in mp.anchor_texts[:2])
                user_parts.append(f'  - Enlazar a {mp.url} usando como texto: {anchors}')
            user_parts.append("  Estos links son OBLIGATORIOS. Insértalos donde fluyan naturalmente.")

        # Internal links a artículos existentes
        if existing_posts:
            user_parts.append("\nARTÍCULOS EXISTENTES DEL BLOG (enlazar 2-3 de forma natural):")
            for ep in existing_posts[:5]:
                user_parts.append(f'  - "{ep["titulo"]}" → {ep["url"]}')
            user_parts.append("  Inserta links a 2-3 de estos artículos donde sea relevante.")

        user_parts.append(f"""
FORMATO DE SALIDA:
==================
Primero genera estas líneas (una por línea, sin formato extra):
META_TITLE: [título SEO, máx 60 chars, keyword al inicio]
META_DESCRIPTION: [descripción con keyword + CTA, 120-155 chars]
SLUG: [url-amigable-con-keyword]
EXTRACTO: [2 oraciones para preview/redes sociales]

Luego el artículo completo en HTML:
- <h1> para título (puede diferir ligeramente del META_TITLE)
- <h2> para secciones principales
- <h3> para subsecciones
- <p> para párrafos
- <ul>/<li> para listas donde aplique
- <strong> para conceptos clave
- <a href="URL"> para links (tanto internos como al sitio del cliente)
- NO incluir <html>, <head>, <body>
""")

        user_prompt = "\n".join(user_parts)
        return system, user_prompt

    @staticmethod
    def build_review_prompt(
        contenido_html: str,
        keyword_principal: str,
        keywords_secundarias: list[str],
        audit_result: dict,
        client_tone: str,
    ) -> str:
        """
        Construye prompt de revisión basado en los resultados de la auditoría SEO.
        Solo pide arreglar los problemas encontrados.
        """
        problemas = audit_result.get("problemas_criticos", [])
        sugerencias = audit_result.get("sugerencias", [])
        stats = audit_result.get("stats", {})
        
        prompt = f"""Revisa y CORRIGE este artículo según los problemas SEO detectados.

KEYWORD PRINCIPAL: "{keyword_principal}"
KEYWORDS SECUNDARIAS: {', '.join(keywords_secundarias)}
TONO REQUERIDO: {client_tone}

ESTADÍSTICAS ACTUALES:
- Palabras: {stats.get('palabras', 0)}
- Keyword density: {stats.get('keyword_density', 0)}%
- Veces que aparece la keyword: {stats.get('keyword_count', 0)}
- H2s: {stats.get('h2s', 0)}
- Links internos: {stats.get('links_internos', 0)}
"""

        if problemas:
            prompt += "\nPROBLEMAS CRÍTICOS A CORREGIR:\n"
            for p in problemas:
                prompt += f"  {p}\n"
        
        if sugerencias:
            prompt += "\nMEJORAS SUGERIDAS:\n"
            for s in sugerencias:
                prompt += f"  {s}\n"

        prompt += f"""
INSTRUCCIONES:
1. Corrige TODOS los problemas críticos
2. Aplica las mejoras sugeridas donde sea posible
3. NO cambies la estructura general del artículo
4. Mantén el tono {client_tone}
5. Devuelve SOLO el artículo corregido en HTML (sin META_TITLE ni otros campos)

ARTÍCULO A CORREGIR:
{contenido_html}"""

        return prompt


# =============================================================================
# Keyword Strategy Planner
# =============================================================================

class KeywordStrategyPlanner:
    """
    Planifica la estrategia de keywords para un cliente.
    
    Genera:
    - Lista de keywords a atacar (organizadas por cluster)
    - Calendario editorial basado en keywords
    - Priorización por dificultad y volumen estimado
    """

    @staticmethod
    def build_strategy_prompt(
        client_name: str,
        client_industry: str,
        client_services: list[str],
        client_location: str,
        existing_keywords: list[str] = None,
        num_keywords: int = 20,
    ) -> tuple[str, str]:
        """
        Construye prompt para que la IA genere estrategia de keywords.
        
        Returns:
            (system_prompt, user_prompt)
        """
        existing = existing_keywords or []
        
        system = """Eres un consultor SEO experto en estrategia de contenido.
Tu trabajo es planificar qué keywords atacar con un blog para maximizar 
el tráfico orgánico de un negocio.

Responde SOLO en formato JSON válido, sin texto adicional ni backticks."""

        user = f"""Genera una estrategia de keywords para el blog de este negocio:

NEGOCIO: {client_name}
INDUSTRIA: {client_industry}
SERVICIOS/PRODUCTOS: {', '.join(client_services)}
UBICACIÓN: {client_location}
KEYWORDS YA USADAS (no repetir): {', '.join(existing) if existing else 'ninguna'}

Genera {num_keywords} keywords organizadas en clusters temáticos.

FORMATO JSON REQUERIDO:
{{
    "clusters": [
        {{
            "nombre": "Nombre del cluster temático",
            "pillar_keyword": "keyword principal competitiva del cluster",
            "pillar_titulo_sugerido": "Título sugerido para el pillar article",
            "keywords": [
                {{
                    "keyword": "keyword long-tail específica",
                    "intencion": "informacional | transaccional | navegacional",
                    "dificultad_estimada": "baja | media | alta",
                    "volumen_estimado": "alto | medio | bajo",
                    "titulo_sugerido": "Título SEO sugerido para el artículo",
                    "prioridad": 1-5
                }}
            ]
        }}
    ],
    "calendario_sugerido": [
        {{
            "semana": 1,
            "keyword": "keyword a atacar",
            "tipo": "pillar | cluster",
            "razon": "por qué esta semana"
        }}
    ]
}}

CRITERIOS DE SELECCIÓN:
- Mezclar keywords informacionales (atraer tráfico) y transaccionales (convertir)
- Priorizar keywords de cola larga con menor competencia
- Incluir keywords con intención local si aplica (ciudad/región)
- Organizar en clusters de 3-5 keywords por tema
- El pillar de cada cluster debe ser la keyword más competitiva
- Los clusters deben linkear naturalmente a los servicios del negocio
"""
        return system, user

    @staticmethod
    def build_topic_suggestions_prompt(
        keyword: str,
        client_industry: str,
        client_name: str,
    ) -> tuple[str, str]:
        """
        Construye prompt para sugerir temas específicos para una keyword.
        """
        system = "Eres un estratega de contenido SEO. Responde SOLO en JSON válido."
        
        user = f"""Para la keyword "{keyword}" en la industria de {client_industry} 
(negocio: {client_name}), sugiere 5 ángulos únicos para artículos:

FORMATO JSON:
{{
    "keyword": "{keyword}",
    "angulos": [
        {{
            "titulo": "Título SEO optimizado (<60 chars, keyword al inicio)",
            "enfoque": "Descripción breve del ángulo único",
            "keywords_secundarias": ["kw1", "kw2", "kw3"],
            "intencion_busqueda": "¿Qué busca el usuario al buscar esto?",
            "cta_sugerido": "Qué acción debería tomar el lector"
        }}
    ]
}}

Los ángulos deben ser DIFERENTES entre sí y responder a distintas 
intenciones de búsqueda del usuario.
"""
        return system, user


# =============================================================================
# Checklist SEO pre-publicación
# =============================================================================

SEO_CHECKLIST = {
    "critico": [
        "Keyword principal en título (primeras 5 palabras)",
        "Keyword en meta description",
        "Keyword en primer párrafo (primeras 100 palabras)",
        "Keyword en al menos 1 H2",
        "Keyword density entre 1-2%",
        "Mínimo 800 palabras",
        "Al menos 3 secciones H2",
        "Meta description entre 120-155 chars",
        "Título menor a 60 chars",
    ],
    "importante": [
        "Keywords secundarias presentes en el contenido",
        "Al menos 2 internal links a otros artículos del blog",
        "Al menos 1 link a página de servicio del cliente",
        "Slug contiene keyword principal",
        "Imágenes con alt text descriptivo",
        "CTA claro al final del artículo",
    ],
    "recomendado": [
        "Párrafos cortos (3-4 oraciones)",
        "Uso de listas donde aplique",
        "Al menos 1 H3 dentro de un H2",
        "Schema markup Article incluido",
        "Open Graph tags correctos",
        "Canonical URL apuntando al dominio del cliente",
    ],
}
