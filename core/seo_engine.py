"""
BlogEngine - Motor SEO.
Gestiona toda la estrategia SEO de los blogs de cada cliente.

ESTRATEGIA ADAPTATIVA POR CLIENTE:
===================================

Nivel 1 — SUBDIRECTORIO (mejor SEO posible):
  cliente.com/blog → proxy inverso hacia BlogEngine
  ✅ Todo el link juice se queda en el dominio del cliente
  ✅ Google lo ve como parte del mismo sitio
  ⚠️ Requiere acceso al servidor del cliente (Nginx/Caddy/Apache)
  
Nivel 2 — SUBDOMINIO (muy buen SEO):
  blog.cliente.com → CNAME hacia BlogEngine
  ✅ Google lo asocia con el dominio principal
  ✅ Solo requiere un registro DNS (CNAME)
  ✅ El cliente puede hacerlo desde su panel de hosting
  ⚠️ Google lo trata como sitio semi-independiente
  
Nivel 3 — DOMINIO EXTERNO + CANONICAL (SEO aceptable):
  blogengine.app/b/cliente → con <link rel="canonical"> apuntando al cliente
  ✅ No requiere nada del cliente
  ✅ Google sigue el canonical y da crédito al dominio original
  ⚠️ Depende de que Google respete el canonical

Cada cliente se configura con su nivel según lo que permita su hosting.
"""
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# =============================================================================
# Configuración SEO por cliente
# =============================================================================

@dataclass
class ClientSEOConfig:
    """Configuración SEO específica de un cliente."""
    
    # Nivel de integración
    integration_level: str = "subdomain"  # subdirectory, subdomain, external
    
    # URLs
    canonical_domain: str = ""       # Dominio canónico del cliente: www.cliente.com
    blog_base_url: str = ""          # URL base del blog: www.cliente.com/blog o blog.cliente.com
    
    # Proxy inverso (nivel 1)
    proxy_path: str = "/blog"        # Path en el sitio del cliente: /blog, /noticias, /articulos
    
    # Identity
    organization_name: str = ""
    organization_logo: str = ""
    organization_url: str = ""
    
    # Social profiles (para schema)
    social_profiles: list[str] = field(default_factory=list)
    
    # Google
    google_analytics_id: str = ""    # G-XXXXXXX
    google_search_console_token: str = ""  # Para submit de URLs
    
    # Configuración avanzada
    default_author: str = ""
    language: str = "es"
    region: str = "MX"


# =============================================================================
# Generador de Meta Tags
# =============================================================================

class SEOMetaGenerator:
    """
    Genera todos los meta tags necesarios para máximo SEO.
    Incluye: Open Graph, Twitter Cards, canonical, hreflang, robots.
    """

    @staticmethod
    def generate_meta_tags(
        title: str,
        description: str,
        url: str,
        canonical_url: str = "",
        image_url: str = "",
        article_date: Optional[datetime] = None,
        article_modified: Optional[datetime] = None,
        author: str = "",
        keywords: list[str] = None,
        language: str = "es",
        region: str = "MX",
        organization_name: str = "",
        noindex: bool = False,
    ) -> str:
        """Genera bloque completo de meta tags HTML."""
        
        canonical = canonical_url or url
        robots = "noindex, nofollow" if noindex else "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1"
        
        tags = []
        
        # --- Básicos ---
        tags.append(f'<title>{title}</title>')
        tags.append(f'<meta name="description" content="{_escape(description)}">')
        tags.append(f'<meta name="robots" content="{robots}">')
        tags.append(f'<link rel="canonical" href="{canonical}">')
        
        if keywords:
            tags.append(f'<meta name="keywords" content="{", ".join(keywords)}">')
        if author:
            tags.append(f'<meta name="author" content="{_escape(author)}">')
        
        # --- Idioma ---
        tags.append(f'<meta property="og:locale" content="{language}_{region}">')
        tags.append(f'<link rel="alternate" hreflang="{language}" href="{canonical}">')
        tags.append(f'<link rel="alternate" hreflang="x-default" href="{canonical}">')
        
        # --- Open Graph ---
        tags.append(f'<meta property="og:type" content="article">')
        tags.append(f'<meta property="og:title" content="{_escape(title)}">')
        tags.append(f'<meta property="og:description" content="{_escape(description)}">')
        tags.append(f'<meta property="og:url" content="{canonical}">')
        if organization_name:
            tags.append(f'<meta property="og:site_name" content="{_escape(organization_name)}">')
        if image_url:
            tags.append(f'<meta property="og:image" content="{image_url}">')
            tags.append(f'<meta property="og:image:width" content="1200">')
            tags.append(f'<meta property="og:image:height" content="630">')
            tags.append(f'<meta property="og:image:type" content="image/jpeg">')
        if article_date:
            tags.append(f'<meta property="article:published_time" content="{article_date.isoformat()}">')
        if article_modified:
            tags.append(f'<meta property="article:modified_time" content="{article_modified.isoformat()}">')
        
        # --- Twitter Card ---
        tags.append(f'<meta name="twitter:card" content="summary_large_image">')
        tags.append(f'<meta name="twitter:title" content="{_escape(title)}">')
        tags.append(f'<meta name="twitter:description" content="{_escape(description)}">')
        if image_url:
            tags.append(f'<meta name="twitter:image" content="{image_url}">')
        
        return "\n    ".join(tags)


# =============================================================================
# Schema.org Structured Data (JSON-LD)
# =============================================================================

class SchemaGenerator:
    """
    Genera datos estructurados JSON-LD para Google.
    Esto es CRÍTICO para:
    - Rich snippets en resultados de búsqueda
    - Knowledge Graph
    - Google Discover
    - Elegibilidad para features especiales de SERP
    """

    @staticmethod
    def article_schema(
        title: str,
        description: str,
        url: str,
        image_url: str = "",
        date_published: Optional[datetime] = None,
        date_modified: Optional[datetime] = None,
        author_name: str = "",
        organization_name: str = "",
        organization_logo: str = "",
        organization_url: str = "",
        keywords: list[str] = None,
        word_count: int = 0,
    ) -> str:
        """Genera schema Article + Organization en JSON-LD."""
        
        published = date_published.isoformat() if date_published else datetime.utcnow().isoformat()
        modified = date_modified.isoformat() if date_modified else published
        
        schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": title[:110],  # Google recomienda max 110 chars
            "description": description[:300],
            "url": url,
            "datePublished": published,
            "dateModified": modified,
            "inLanguage": "es",
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": url,
            },
        }
        
        if image_url:
            schema["image"] = {
                "@type": "ImageObject",
                "url": image_url,
                "width": 1200,
                "height": 630,
            }
        
        if author_name:
            schema["author"] = {
                "@type": "Person",
                "name": author_name,
            }
        
        if organization_name:
            publisher = {
                "@type": "Organization",
                "name": organization_name,
                "url": organization_url,
            }
            if organization_logo:
                publisher["logo"] = {
                    "@type": "ImageObject",
                    "url": organization_logo,
                }
            schema["publisher"] = publisher
        
        if keywords:
            schema["keywords"] = ", ".join(keywords)
        
        if word_count:
            schema["wordCount"] = word_count
        
        import json
        return f'<script type="application/ld+json">\n{json.dumps(schema, ensure_ascii=False, indent=2)}\n</script>'

    @staticmethod
    def breadcrumb_schema(items: list[dict]) -> str:
        """
        Genera schema BreadcrumbList.
        
        Args:
            items: [{"name": "Inicio", "url": "https://..."}, {"name": "Blog", "url": "..."}, ...]
        """
        schema = {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": i + 1,
                    "name": item["name"],
                    "item": item["url"],
                }
                for i, item in enumerate(items)
            ],
        }
        
        import json
        return f'<script type="application/ld+json">\n{json.dumps(schema, ensure_ascii=False, indent=2)}\n</script>'

    @staticmethod
    def organization_schema(
        name: str,
        url: str,
        logo: str = "",
        description: str = "",
        social_profiles: list[str] = None,
    ) -> str:
        """Genera schema Organization para la página principal del blog."""
        schema = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": name,
            "url": url,
        }
        if logo:
            schema["logo"] = logo
        if description:
            schema["description"] = description
        if social_profiles:
            schema["sameAs"] = social_profiles
        
        import json
        return f'<script type="application/ld+json">\n{json.dumps(schema, ensure_ascii=False, indent=2)}\n</script>'

    @staticmethod
    def blog_posting_list_schema(posts: list[dict], blog_url: str) -> str:
        """Genera schema para lista de artículos (CollectionPage)."""
        schema = {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "url": blog_url,
            "mainEntity": {
                "@type": "ItemList",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": i + 1,
                        "url": post["url"],
                        "name": post["title"],
                    }
                    for i, post in enumerate(posts)
                ],
            },
        }
        
        import json
        return f'<script type="application/ld+json">\n{json.dumps(schema, ensure_ascii=False, indent=2)}\n</script>'


# =============================================================================
# Generador de URL canónica por estrategia
# =============================================================================

class CanonicalURLBuilder:
    """
    Construye URLs canónicas según el nivel de integración del cliente.
    
    Nivel 1 (subdirectory): https://www.cliente.com/blog/mi-articulo
    Nivel 2 (subdomain):    https://blog.cliente.com/mi-articulo  
    Nivel 3 (external):     https://www.cliente.com/blog/mi-articulo (canonical apunta aquí aunque el contenido esté en blogengine.app)
    """

    @staticmethod
    def build_post_url(seo_config: ClientSEOConfig, post_slug: str) -> str:
        """Construye la URL pública del post."""
        if seo_config.blog_base_url:
            base = seo_config.blog_base_url.rstrip("/")
            return f"{base}/{post_slug}"
        return f"https://blogengine.app/b/default/{post_slug}"

    @staticmethod
    def build_canonical_url(seo_config: ClientSEOConfig, post_slug: str) -> str:
        """
        Construye la URL canónica.
        
        Para nivel 3 (external), el canonical apunta al dominio del cliente
        aunque el contenido se sirva desde blogengine.app.
        Esto le dice a Google: "el crédito SEO es para el dominio del cliente".
        """
        if seo_config.integration_level == "external" and seo_config.canonical_domain:
            # El contenido vive en blogengine.app pero el canonical apunta al cliente
            path = seo_config.proxy_path.strip("/")
            return f"https://{seo_config.canonical_domain}/{path}/{post_slug}"
        
        return CanonicalURLBuilder.build_post_url(seo_config, post_slug)

    @staticmethod
    def build_blog_home_url(seo_config: ClientSEOConfig) -> str:
        """Construye URL de la home del blog."""
        if seo_config.blog_base_url:
            return seo_config.blog_base_url.rstrip("/")
        return "https://blogengine.app"


# =============================================================================
# Generador de Sitemap XML avanzado
# =============================================================================

class SitemapGenerator:
    """
    Genera sitemaps XML con todas las optimizaciones SEO.
    Incluye: lastmod, changefreq, priority, image sitemap.
    """

    @staticmethod
    def generate(
        posts: list[dict],
        blog_home_url: str,
        seo_config: ClientSEOConfig,
    ) -> str:
        """
        Genera sitemap.xml completo.
        
        Args:
            posts: [{"slug": "...", "title": "...", "date": datetime, "image": "..."}]
            blog_home_url: URL de la home del blog
            seo_config: Configuración SEO del cliente
        """
        urls = []
        
        # Home del blog
        urls.append(f"""  <url>
    <loc>{blog_home_url}</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>""")

        # Artículos
        for post in posts:
            post_url = CanonicalURLBuilder.build_canonical_url(seo_config, post["slug"])
            lastmod = post.get("date", datetime.utcnow()).strftime("%Y-%m-%d")
            
            image_tag = ""
            if post.get("image"):
                image_tag = f"""
    <image:image>
      <image:loc>{post["image"]}</image:loc>
      <image:title>{_escape(post.get("title", ""))}</image:title>
    </image:image>"""
            
            urls.append(f"""  <url>
    <loc>{post_url}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>{image_tag}
  </url>""")

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
{chr(10).join(urls)}
</urlset>"""

        return xml


# =============================================================================
# Generador de Robots.txt
# =============================================================================

class RobotsTxtGenerator:
    """Genera robots.txt optimizado para SEO."""

    @staticmethod
    def generate(sitemap_url: str) -> str:
        return f"""User-agent: *
Allow: /

# Sitemap
Sitemap: {sitemap_url}

# Bloquear rutas de admin/API
Disallow: /api/
Disallow: /admin/
Disallow: /embed/
"""


# =============================================================================
# Internal Linking Engine
# =============================================================================

class InternalLinkingEngine:
    """
    Motor de internal linking automático.
    
    Analiza el contenido de un artículo y sugiere/inserta links
    a otros artículos del mismo blog. Esto es CRUCIAL para SEO porque:
    - Distribuye PageRank entre artículos
    - Ayuda a Google a descubrir y entender la estructura del sitio
    - Aumenta el tiempo en sitio del usuario
    """

    @staticmethod
    def suggest_internal_links(
        current_post_content: str,
        current_post_slug: str,
        other_posts: list[dict],
        seo_config: ClientSEOConfig,
        max_links: int = 3,
    ) -> list[dict]:
        """
        Sugiere internal links basado en coincidencia de keywords.
        
        Args:
            current_post_content: HTML del artículo actual
            current_post_slug: Slug del artículo actual (para no linkear a sí mismo)
            other_posts: [{"slug": "...", "title": "...", "keyword": "...", "extracto": "..."}]
            seo_config: Config SEO del cliente
            max_links: Máximo de links a sugerir
        
        Returns:
            [{"url": "...", "title": "...", "anchor_text": "...", "keyword": "..."}]
        """
        suggestions = []
        content_lower = current_post_content.lower()

        for post in other_posts:
            if post["slug"] == current_post_slug:
                continue
            
            keyword = post.get("keyword", "").lower()
            if keyword and keyword in content_lower:
                url = CanonicalURLBuilder.build_post_url(seo_config, post["slug"])
                suggestions.append({
                    "url": url,
                    "title": post["title"],
                    "anchor_text": post.get("keyword", post["title"]),
                    "keyword": keyword,
                })
        
        return suggestions[:max_links]

    @staticmethod
    def inject_internal_links(html_content: str, links: list[dict]) -> str:
        """
        Inyecta internal links en el contenido HTML.
        Reemplaza la primera aparición de cada keyword con un link.
        """
        for link in links:
            keyword = link["keyword"]
            anchor = f'<a href="{link["url"]}" title="{_escape(link["title"])}">{keyword}</a>'
            
            # Solo reemplazar la primera aparición que NO esté ya dentro de un link
            # Búsqueda simple: reemplazar primera ocurrencia en texto plano
            if keyword.lower() in html_content.lower():
                # Encontrar la primera ocurrencia que no esté dentro de un <a> tag
                import re
                pattern = re.compile(
                    rf'(?<!<a[^>]*>)(?<!</a>)\b({re.escape(keyword)})\b',
                    re.IGNORECASE,
                )
                html_content = pattern.sub(anchor, html_content, count=1)
        
        return html_content


# =============================================================================
# Guías de configuración por nivel
# =============================================================================

class SetupGuideGenerator:
    """
    Genera instrucciones de configuración para cada nivel de integración.
    El cliente o Alex puede seguir estos pasos.
    """

    @staticmethod
    def generate_guide(
        integration_level: str,
        client_domain: str,
        blog_slug: str,
    ) -> dict:
        """Genera guía de configuración según el nivel."""
        
        guides = {
            "subdirectory": {
                "titulo": "Configuración de Subdirectorio (Máximo SEO)",
                "descripcion": f"El blog aparecerá en {client_domain}/blog",
                "beneficio_seo": "⭐⭐⭐⭐⭐ Máximo - Todo el link juice va al dominio del cliente",
                "dificultad": "Media - Requiere acceso al servidor",
                "pasos": [
                    {
                        "paso": "1. Configurar Nginx como proxy inverso",
                        "codigo": f"""# Agregar al archivo de configuración de Nginx del cliente
# /etc/nginx/sites-available/{client_domain}

location /blog {{
    proxy_pass https://blogengine.app/b/{blog_slug};
    proxy_set_header Host blogengine.app;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Original-Host {client_domain};
    
    # Importante: NO cambiar las URLs en las respuestas
    proxy_redirect off;
    
    # Cache para velocidad
    proxy_cache_valid 200 1h;
}}""",
                    },
                    {
                        "paso": "1b. Alternativa con Caddy (más simple)",
                        "codigo": f"""{client_domain} {{
    handle /blog/* {{
        reverse_proxy blogengine.app {{
            header_up Host blogengine.app
            header_up X-Original-Host {client_domain}
        }}
    }}
    
    # Resto del sitio
    handle {{
        # configuración existente del sitio
    }}
}}""",
                    },
                    {
                        "paso": "1c. Alternativa con Apache (.htaccess)",
                        "codigo": f"""# Agregar al .htaccess del cliente
RewriteEngine On
RewriteRule ^blog/(.*)$ https://blogengine.app/b/{blog_slug}/$1 [P,L]
ProxyPassReverse /blog/ https://blogengine.app/b/{blog_slug}/""",
                    },
                    {
                        "paso": "2. Verificar en BlogEngine",
                        "detalle": f"Configurar el cliente con:\n- integration_level: 'subdirectory'\n- canonical_domain: '{client_domain}'\n- blog_base_url: 'https://{client_domain}/blog'\n- proxy_path: '/blog'",
                    },
                    {
                        "paso": "3. Probar",
                        "detalle": f"Visitar https://{client_domain}/blog y verificar que carga el blog correctamente.",
                    },
                ],
            },
            "subdomain": {
                "titulo": "Configuración de Subdominio (Buen SEO, fácil setup)",
                "descripcion": f"El blog aparecerá en blog.{client_domain}",
                "beneficio_seo": "⭐⭐⭐⭐ Muy bueno - Google lo asocia con el dominio principal",
                "dificultad": "Fácil - Solo un registro DNS",
                "pasos": [
                    {
                        "paso": "1. Agregar registro CNAME en el DNS del cliente",
                        "codigo": f"""# En el panel DNS del hosting del cliente:
Tipo:  CNAME
Host:  blog
Valor: blogengine.app
TTL:   3600""",
                    },
                    {
                        "paso": "2. Configurar en BlogEngine",
                        "detalle": f"Configurar el cliente con:\n- integration_level: 'subdomain'\n- blog_domain: 'blog.{client_domain}'\n- canonical_domain: 'blog.{client_domain}'\n- blog_base_url: 'https://blog.{client_domain}'",
                    },
                    {
                        "paso": "3. SSL automático",
                        "detalle": "BlogEngine genera certificado SSL automáticamente vía Let's Encrypt / Traefik.",
                    },
                    {
                        "paso": "4. Verificar",
                        "detalle": f"Esperar propagación DNS (hasta 24h) y visitar https://blog.{client_domain}",
                    },
                ],
            },
            "external": {
                "titulo": "Configuración Externa con Canonical (SEO básico, cero setup en cliente)",
                "descripcion": f"El blog vive en blogengine.app pero Google da crédito a {client_domain}",
                "beneficio_seo": "⭐⭐⭐ Aceptable - Depende del canonical tag. Funciona como backlink fuerte",
                "dificultad": "Ninguna - No se toca nada del cliente",
                "pasos": [
                    {
                        "paso": "1. Configurar en BlogEngine",
                        "detalle": f"Configurar el cliente con:\n- integration_level: 'external'\n- blog_slug: '{blog_slug}'\n- canonical_domain: '{client_domain}'\n- blog_base_url: 'https://blogengine.app/b/{blog_slug}'",
                    },
                    {
                        "paso": "2. Agregar link al blog desde el sitio del cliente",
                        "codigo": f'<a href="https://blogengine.app/b/{blog_slug}">Visita nuestro Blog</a>',
                    },
                    {
                        "paso": "3. (Opcional) Embed widget en el sitio del cliente",
                        "codigo": f"""<!-- Pegar en cualquier página del sitio del cliente -->
<div id="blogengine-posts"></div>
<script src="https://blogengine.app/embed/{blog_slug}.js"></script>""",
                    },
                ],
                "nota_seo": "El canonical tag le dice a Google que el contenido original pertenece al dominio del cliente. Google puede o no respetar esto, pero con backlinks adicionales y Search Console se refuerza.",
            },
        }
        
        return guides.get(integration_level, guides["subdomain"])


# =============================================================================
# Google Indexing - Submit URLs
# =============================================================================

class GoogleIndexingService:
    """
    Envía URLs a Google para indexación rápida.
    
    Dos métodos:
    1. Google Indexing API (requiere verificación en Search Console)
    2. Ping al sitemap (siempre funciona, más lento)
    """

    @staticmethod
    async def ping_sitemap(sitemap_url: str) -> bool:
        """Notifica a Google que el sitemap ha sido actualizado."""
        import httpx
        try:
            url = f"https://www.google.com/ping?sitemap={sitemap_url}"
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                success = response.status_code == 200
                logger.info(f"[GoogleIndexing] Ping sitemap {'✅' if success else '❌'}: {sitemap_url}")
                return success
        except Exception as e:
            logger.error(f"[GoogleIndexing] Error ping sitemap: {e}")
            return False

    @staticmethod
    async def submit_url_indexing_api(url: str, credentials_json: str) -> bool:
        """
        Envía URL a Google Indexing API para indexación inmediata.
        Requiere credenciales de servicio de Google.
        
        TODO: Implementar con google-auth y google-api-python-client
        """
        logger.info(f"[GoogleIndexing] Submit URL (pendiente de implementar): {url}")
        return False

    @staticmethod
    async def ping_bing_sitemap(sitemap_url: str) -> bool:
        """Notifica a Bing también."""
        import httpx
        try:
            url = f"https://www.bing.com/ping?sitemap={sitemap_url}"
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                return response.status_code == 200
        except Exception:
            return False


# =============================================================================
# Utilidades
# =============================================================================

def _escape(text: str) -> str:
    """Escapa texto para uso seguro en atributos HTML."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def count_words(html_content: str) -> int:
    """Cuenta palabras en contenido HTML (removiendo tags)."""
    import re
    text = re.sub(r'<[^>]+>', '', html_content)
    return len(text.split())
