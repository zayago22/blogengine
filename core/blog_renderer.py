"""
BlogEngine - Blog Renderer.
Sirve los blogs de cada cliente directamente desde la plataforma.

Estrategia de acceso:
  1. Subdominio: cliente.blogengine.app
  2. Dominio personalizado: blog.clientesite.com (CNAME → blogengine.app)
  3. Slug directo: blogengine.app/b/cliente

El sistema detecta automáticamente qué cliente es por:
  - Host header (subdominio o dominio personalizado)
  - Slug en la URL

Cada blog tiene:
  - Diseño personalizable (colores, logo, tipografía)
  - SEO completo (meta tags, Open Graph, sitemap.xml, robots.txt)
  - Server-side rendered (HTML puro, sin JS obligatorio → Google lo indexa perfecto)
"""
import logging
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from models.base import get_db
from models.client import Client
from models.blog_post import BlogPost

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Resolución de cliente por dominio/subdominio
# =============================================================================

async def resolver_cliente(request: Request, db: AsyncSession) -> Optional[Client]:
    """
    Detecta qué cliente corresponde según el Host header.
    
    Prioridad:
      1. Dominio personalizado: blog.clientesite.com → busca en client.blog_domain
      2. Subdominio: mi-cliente.blogengine.app → busca en client.blog_slug
      3. None si no encuentra
    """
    host = request.headers.get("host", "").split(":")[0].lower()
    
    # 1. Buscar por dominio personalizado
    result = await db.execute(
        select(Client).where(
            Client.blog_domain == host,
            Client.estado == "activo",
        )
    )
    client = result.scalar_one_or_none()
    if client:
        return client

    # 2. Buscar por subdominio (slug.blogengine.app)
    base_domain = "blogengine.app"  # Configurar en .env
    if host.endswith(f".{base_domain}"):
        slug = host.replace(f".{base_domain}", "")
        result = await db.execute(
            select(Client).where(
                Client.blog_slug == slug,
                Client.estado == "activo",
            )
        )
        client = result.scalar_one_or_none()
        if client:
            return client

    return None


# =============================================================================
# Plantilla HTML base para blogs
# =============================================================================

def render_blog_layout(client: Client, content: str, title: str = "", 
                       meta_description: str = "", og_image: str = "",
                       canonical_url: str = "",
                       schema_json_ld: str = "",
                       article_date=None) -> str:
    """
    Renderiza el layout completo del blog de un cliente.
    Server-side rendered, HTML puro, SEO optimizado al máximo.
    """
    from core.seo_engine import SEOMetaGenerator, ClientSEOConfig
    
    # Configuración de diseño del cliente
    colors = client.blog_design or {}
    primary_color = colors.get("primary", "#2563eb")
    bg_color = colors.get("background", "#ffffff")
    text_color = colors.get("text", "#1f2937")
    accent_color = colors.get("accent", "#3b82f6")
    font_family = colors.get("font", "'Inter', sans-serif")
    logo_url = colors.get("logo_url", "")

    page_title = f"{title} | {client.nombre}" if title else f"Blog | {client.nombre}"
    description = meta_description or f"Blog de {client.nombre} - {client.descripcion_negocio or ''}"

    # Construir URL canónica correcta según nivel de integración
    seo_config = _build_seo_config(client)
    if not canonical_url:
        from core.seo_engine import CanonicalURLBuilder
        canonical_url = CanonicalURLBuilder.build_blog_home_url(seo_config)

    # Generar meta tags SEO completos
    meta_tags = SEOMetaGenerator.generate_meta_tags(
        title=page_title,
        description=description,
        url=canonical_url,
        canonical_url=canonical_url,
        image_url=og_image,
        article_date=article_date,
        author=client.seo_default_author or "",
        language=client.idioma or "es",
        region="MX",
        organization_name=client.nombre,
    )
    
    # Google Analytics
    ga_script = ""
    ga_id = client.seo_google_analytics_id
    if ga_id:
        ga_script = f"""
    <script async src="https://www.googletagmanager.com/gtag/js?id={ga_id}"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', '{ga_id}');
    </script>"""

    return f"""<!DOCTYPE html>
<html lang="{client.idioma or 'es'}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <!-- SEO Meta Tags (generados por BlogEngine) -->
    {meta_tags}
    
    <!-- Schema.org JSON-LD -->
    {schema_json_ld}
    
    <!-- Google Analytics -->
    {ga_script}
    
    <!-- Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        :root {{
            --primary: {primary_color};
            --bg: {bg_color};
            --text: {text_color};
            --accent: {accent_color};
            --font: {font_family};
        }}
        
        body {{
            font-family: var(--font);
            background: var(--bg);
            color: var(--text);
            line-height: 1.7;
        }}
        
        /* Header */
        .blog-header {{
            border-bottom: 1px solid #e5e7eb;
            padding: 1rem 0;
            background: white;
        }}
        .blog-header .container {{
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .blog-logo {{
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--primary);
            text-decoration: none;
        }}
        .blog-logo img {{
            height: 40px;
        }}
        .blog-nav a {{
            color: var(--text);
            text-decoration: none;
            margin-left: 1.5rem;
            font-weight: 500;
        }}
        .blog-nav a:hover {{
            color: var(--primary);
        }}
        
        /* Container */
        .container {{
            max-width: 800px;
            margin: 0 auto;
            padding: 0 1.5rem;
        }}
        .container-wide {{
            max-width: 1100px;
            margin: 0 auto;
            padding: 0 1.5rem;
        }}
        
        /* Article list */
        .blog-list {{
            padding: 3rem 0;
        }}
        .blog-card {{
            margin-bottom: 2.5rem;
            padding-bottom: 2.5rem;
            border-bottom: 1px solid #f3f4f6;
        }}
        .blog-card:last-child {{
            border-bottom: none;
        }}
        .blog-card h2 {{
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
        }}
        .blog-card h2 a {{
            color: var(--text);
            text-decoration: none;
        }}
        .blog-card h2 a:hover {{
            color: var(--primary);
        }}
        .blog-card .meta {{
            color: #6b7280;
            font-size: 0.875rem;
            margin-bottom: 0.75rem;
        }}
        .blog-card .extracto {{
            color: #4b5563;
        }}
        .blog-card .leer-mas {{
            display: inline-block;
            margin-top: 0.75rem;
            color: var(--primary);
            font-weight: 500;
            text-decoration: none;
        }}
        
        /* Single article */
        .article {{
            padding: 3rem 0;
        }}
        .article h1 {{
            font-size: 2.25rem;
            line-height: 1.3;
            margin-bottom: 1rem;
        }}
        .article .meta {{
            color: #6b7280;
            margin-bottom: 2rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid #f3f4f6;
        }}
        .article-body h2 {{
            font-size: 1.5rem;
            margin: 2rem 0 1rem;
            color: var(--text);
        }}
        .article-body h3 {{
            font-size: 1.25rem;
            margin: 1.5rem 0 0.75rem;
        }}
        .article-body p {{
            margin-bottom: 1.25rem;
        }}
        .article-body ul, .article-body ol {{
            margin: 1rem 0 1.25rem 1.5rem;
        }}
        .article-body li {{
            margin-bottom: 0.5rem;
        }}
        .article-body img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            margin: 1.5rem 0;
        }}
        .article-body strong {{
            font-weight: 600;
        }}
        .article-body a {{
            color: var(--primary);
        }}
        
        /* CTA box */
        .cta-box {{
            background: #f0f7ff;
            border: 1px solid #dbeafe;
            border-radius: 12px;
            padding: 2rem;
            margin: 2.5rem 0;
            text-align: center;
        }}
        .cta-box h3 {{
            margin-bottom: 0.5rem;
        }}
        .cta-box a {{
            display: inline-block;
            background: var(--primary);
            color: white;
            padding: 0.75rem 2rem;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            margin-top: 1rem;
        }}
        
        /* Footer */
        .blog-footer {{
            border-top: 1px solid #e5e7eb;
            padding: 2rem 0;
            text-align: center;
            color: #9ca3af;
            font-size: 0.875rem;
        }}
        
        /* Powered by - backlink SEO para BlogEngine */
        .powered-by {{
            margin-top: 0.5rem;
            font-size: 0.75rem;
        }}
        .powered-by a {{
            color: #9ca3af;
            text-decoration: none;
        }}
        .powered-by a:hover {{
            color: var(--primary);
        }}
        
        /* Responsive */
        @media (max-width: 640px) {{
            .article h1 {{
                font-size: 1.75rem;
            }}
            .blog-header .container {{
                flex-direction: column;
                gap: 0.75rem;
            }}
        }}
    </style>
</head>
<body>
    <header class="blog-header">
        <div class="container-wide">
            <a href="/" class="blog-logo">
                {f'<img src="{logo_url}" alt="{client.nombre}">' if logo_url else client.nombre}
            </a>
            <nav class="blog-nav">
                <a href="/">Blog</a>
                <a href="{client.sitio_web}" target="_blank">Sitio Web</a>
            </nav>
        </div>
    </header>
    
    <main>
        {content}
    </main>
    
    <footer class="blog-footer">
        <div class="container">
            <p>&copy; {client.nombre}. Todos los derechos reservados.</p>
            <p class="powered-by">
                Powered by <a href="https://blogengine.app" target="_blank">BlogEngine</a>
            </p>
        </div>
    </footer>
</body>
</html>"""


def render_article_card(post: BlogPost, base_path: str = "") -> str:
    """Renderiza tarjeta de un artículo para la lista del blog."""
    fecha = post.fecha_publicado or post.created_at
    fecha_str = fecha.strftime("%d de %B, %Y") if fecha else ""
    
    return f"""
    <article class="blog-card">
        <h2><a href="{base_path}/{post.slug}">{post.titulo}</a></h2>
        <div class="meta">{fecha_str}</div>
        <p class="extracto">{post.extracto or ''}</p>
        <a href="{base_path}/{post.slug}" class="leer-mas">Leer más →</a>
    </article>"""


# =============================================================================
# Endpoints del blog público
# =============================================================================

@router.get("/b/{blog_slug}", response_class=HTMLResponse)
async def blog_home_by_slug(blog_slug: str, db: AsyncSession = Depends(get_db)):
    """Home del blog accedido por slug: blogengine.app/b/mi-cliente"""
    result = await db.execute(
        select(Client).where(Client.blog_slug == blog_slug, Client.estado == "activo")
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Blog no encontrado")
    
    return await _render_blog_home(client, db, base_path=f"/b/{blog_slug}")


@router.get("/b/{blog_slug}/{post_slug}", response_class=HTMLResponse)
async def blog_post_by_slug(blog_slug: str, post_slug: str, db: AsyncSession = Depends(get_db)):
    """Artículo individual accedido por slug."""
    result = await db.execute(
        select(Client).where(Client.blog_slug == blog_slug, Client.estado == "activo")
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Blog no encontrado")
    
    return await _render_blog_post(client, post_slug, db, base_path=f"/b/{blog_slug}")


@router.get("/b/{blog_slug}/sitemap.xml")
async def blog_sitemap(blog_slug: str, db: AsyncSession = Depends(get_db)):
    """Sitemap XML para SEO."""
    result = await db.execute(
        select(Client).where(Client.blog_slug == blog_slug, Client.estado == "activo")
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404)
    
    return await _render_sitemap(client, db, base_path=f"/b/{blog_slug}")


@router.get("/b/{blog_slug}/rss.xml")
async def blog_rss(blog_slug: str, db: AsyncSession = Depends(get_db)):
    """Feed RSS para suscriptores."""
    result = await db.execute(
        select(Client).where(Client.blog_slug == blog_slug, Client.estado == "activo")
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404)
    
    return await _render_rss(client, db, base_path=f"/b/{blog_slug}")


# =============================================================================
# API pública JSON (para clientes que quieran integrar con JS)
# =============================================================================

@router.get("/api/public/{blog_slug}/posts")
async def api_public_posts(blog_slug: str, limit: int = 10, db: AsyncSession = Depends(get_db)):
    """
    API pública JSON de los posts de un blog.
    Los clientes pueden usar esto para integrar el blog en su sitio con JS.
    
    Ejemplo de uso en el sitio del cliente:
        <div id="blog-posts"></div>
        <script>
            fetch('https://blogengine.app/api/public/mi-empresa/posts')
                .then(r => r.json())
                .then(posts => {
                    // Renderizar posts
                })
        </script>
    """
    result = await db.execute(
        select(Client).where(Client.blog_slug == blog_slug, Client.estado == "activo")
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404)

    result = await db.execute(
        select(BlogPost)
        .where(BlogPost.client_id == client.id, BlogPost.estado == "publicado")
        .order_by(desc(BlogPost.fecha_publicado))
        .limit(limit)
    )
    posts = result.scalars().all()

    return [
        {
            "titulo": p.titulo,
            "slug": p.slug,
            "extracto": p.extracto,
            "meta_description": p.meta_description,
            "imagen_destacada_url": p.imagen_destacada_url,
            "fecha_publicado": p.fecha_publicado.isoformat() if p.fecha_publicado else None,
            "url": f"/b/{blog_slug}/{p.slug}",
            "keyword": p.keyword_principal,
        }
        for p in posts
    ]


@router.get("/api/public/{blog_slug}/posts/{post_slug}")
async def api_public_post_detail(blog_slug: str, post_slug: str, db: AsyncSession = Depends(get_db)):
    """API pública: detalle completo de un artículo en JSON."""
    result = await db.execute(
        select(Client).where(Client.blog_slug == blog_slug, Client.estado == "activo")
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404)

    result = await db.execute(
        select(BlogPost).where(
            BlogPost.client_id == client.id,
            BlogPost.slug == post_slug,
            BlogPost.estado == "publicado",
        )
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404)

    return {
        "titulo": post.titulo,
        "slug": post.slug,
        "meta_description": post.meta_description,
        "contenido_html": post.contenido_html,
        "extracto": post.extracto,
        "imagen_destacada_url": post.imagen_destacada_url,
        "fecha_publicado": post.fecha_publicado.isoformat() if post.fecha_publicado else None,
        "keyword": post.keyword_principal,
        "tags": post.tags,
    }


# =============================================================================
# Script embebible (para clientes que quieran widget JS)
# =============================================================================

@router.get("/embed/{blog_slug}.js")
async def blog_embed_script(blog_slug: str):
    """
    Script JS embebible. El cliente pega esto en su sitio:
    <div id="blogengine-posts"></div>
    <script src="https://blogengine.app/embed/mi-empresa.js"></script>
    """
    js = f"""
(function() {{
    const API = 'https://blogengine.app/api/public/{blog_slug}/posts';
    const container = document.getElementById('blogengine-posts');
    if (!container) return;
    
    fetch(API)
        .then(r => r.json())
        .then(posts => {{
            container.innerHTML = posts.map(p => `
                <article style="margin-bottom:2rem;padding-bottom:2rem;border-bottom:1px solid #eee;">
                    <h3 style="margin-bottom:0.5rem;">
                        <a href="https://blogengine.app/b/{blog_slug}/${{p.slug}}" 
                           target="_blank" style="color:inherit;text-decoration:none;">
                            ${{p.titulo}}
                        </a>
                    </h3>
                    <p style="color:#666;margin-bottom:0.5rem;">${{p.extracto || ''}}</p>
                    <a href="https://blogengine.app/b/{blog_slug}/${{p.slug}}" 
                       target="_blank" style="color:#2563eb;">
                        Leer más →
                    </a>
                </article>
            `).join('');
        }})
        .catch(() => {{
            container.innerHTML = '<p>No se pudieron cargar los artículos.</p>';
        }});
}})();
"""
    return Response(content=js, media_type="application/javascript")


# =============================================================================
# Renderizadores internos
# =============================================================================

async def _render_blog_home(client: Client, db: AsyncSession, base_path: str) -> HTMLResponse:
    """Renderiza la página principal del blog con SEO completo."""
    from core.seo_engine import SchemaGenerator, CanonicalURLBuilder
    
    result = await db.execute(
        select(BlogPost)
        .where(BlogPost.client_id == client.id, BlogPost.estado == "publicado")
        .order_by(desc(BlogPost.fecha_publicado))
        .limit(20)
    )
    posts = result.scalars().all()

    seo_config = _build_seo_config(client)
    blog_home_url = CanonicalURLBuilder.build_blog_home_url(seo_config)

    if not posts:
        articles_html = """
        <div style="text-align:center;padding:4rem 0;color:#9ca3af;">
            <p style="font-size:1.25rem;">Próximamente publicaremos contenido aquí.</p>
            <p>¡Vuelve pronto!</p>
        </div>"""
    else:
        articles_html = "\n".join(
            render_article_card(p, base_path) for p in posts
        )

    # Schema: Organization + CollectionPage
    schema = SchemaGenerator.organization_schema(
        name=client.nombre,
        url=client.sitio_web,
        logo=(client.blog_design or {}).get("logo_url", ""),
        description=client.descripcion_negocio or "",
        social_profiles=client.seo_social_profiles or [],
    )
    
    if posts:
        posts_data = [
            {"url": CanonicalURLBuilder.build_post_url(seo_config, p.slug), "title": p.titulo}
            for p in posts
        ]
        schema += "\n" + SchemaGenerator.blog_posting_list_schema(posts_data, blog_home_url)

    content = f"""
    <section class="blog-list">
        <div class="container">
            <h1 style="font-size:2rem;margin-bottom:2rem;">Blog</h1>
            {articles_html}
        </div>
    </section>"""

    html = render_blog_layout(client, content, schema_json_ld=schema, canonical_url=blog_home_url)
    return HTMLResponse(content=html)


async def _render_blog_post(
    client: Client, post_slug: str, db: AsyncSession, base_path: str
) -> HTMLResponse:
    """Renderiza un artículo individual con SEO completo."""
    from core.seo_engine import (
        SchemaGenerator, CanonicalURLBuilder, InternalLinkingEngine, count_words
    )
    
    result = await db.execute(
        select(BlogPost).where(
            BlogPost.client_id == client.id,
            BlogPost.slug == post_slug,
            BlogPost.estado == "publicado",
        )
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")

    seo_config = _build_seo_config(client)
    canonical_url = CanonicalURLBuilder.build_canonical_url(seo_config, post.slug)
    blog_home_url = CanonicalURLBuilder.build_blog_home_url(seo_config)

    fecha = post.fecha_publicado or post.created_at
    fecha_str = fecha.strftime("%d de %B, %Y") if fecha else ""
    
    # Internal linking: buscar otros posts para enlazar
    contenido_html = post.contenido_html or ""
    result_others = await db.execute(
        select(BlogPost)
        .where(
            BlogPost.client_id == client.id,
            BlogPost.estado == "publicado",
            BlogPost.id != post.id,
        )
        .limit(20)
    )
    other_posts = result_others.scalars().all()
    
    if other_posts:
        other_posts_data = [
            {"slug": p.slug, "title": p.titulo, "keyword": p.keyword_principal or "", "extracto": p.extracto or ""}
            for p in other_posts
        ]
        links = InternalLinkingEngine.suggest_internal_links(
            contenido_html, post.slug, other_posts_data, seo_config
        )
        if links:
            contenido_html = InternalLinkingEngine.inject_internal_links(contenido_html, links)

    # Schema: Article + BreadcrumbList
    word_count = count_words(contenido_html)
    schema = SchemaGenerator.article_schema(
        title=post.titulo,
        description=post.meta_description or post.extracto or "",
        url=canonical_url,
        image_url=post.imagen_destacada_url or "",
        date_published=post.fecha_publicado,
        date_modified=post.updated_at if hasattr(post, 'updated_at') else post.fecha_publicado,
        author_name=client.seo_default_author or client.nombre,
        organization_name=client.nombre,
        organization_logo=(client.blog_design or {}).get("logo_url", ""),
        organization_url=client.sitio_web,
        keywords=[post.keyword_principal] + (post.keywords_secundarias or []) if post.keyword_principal else [],
        word_count=word_count,
    )
    
    # Breadcrumbs
    schema += "\n" + SchemaGenerator.breadcrumb_schema([
        {"name": "Inicio", "url": client.sitio_web},
        {"name": "Blog", "url": blog_home_url},
        {"name": post.titulo, "url": canonical_url},
    ])

    # Related posts para el final del artículo
    related_html = ""
    if other_posts[:3]:
        related_cards = "\n".join(
            f'<a href="{base_path}/{p.slug}" style="text-decoration:none;color:inherit;">'
            f'<div style="padding:1rem;border:1px solid #e5e7eb;border-radius:8px;">'
            f'<h4 style="margin:0 0 0.25rem;color:var(--primary);">{p.titulo}</h4>'
            f'<p style="margin:0;font-size:0.875rem;color:#6b7280;">{(p.extracto or "")[:100]}</p>'
            f'</div></a>'
            for p in other_posts[:3]
        )
        related_html = f"""
            <div style="margin-top:3rem;padding-top:2rem;border-top:1px solid #e5e7eb;">
                <h3 style="margin-bottom:1rem;">Artículos relacionados</h3>
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:1rem;">
                    {related_cards}
                </div>
            </div>"""

    cta_text = client.blog_cta_text or "Conoce nuestros servicios"
    cta_url = client.blog_cta_url or client.sitio_web

    content = f"""
    <article class="article">
        <div class="container">
            <h1>{post.titulo}</h1>
            <div class="meta">{fecha_str} · {word_count} palabras · Lectura de {max(1, word_count // 200)} min</div>
            <div class="article-body">
                {contenido_html}
            </div>
            
            <div class="cta-box">
                <h3>{cta_text}</h3>
                <p>Visita nuestro sitio para conocer más.</p>
                <a href="{cta_url}" target="_blank">Visitar {client.nombre}</a>
            </div>
            
            {related_html}
            
            <div style="margin-top:2rem;">
                <a href="{base_path}" style="color:var(--primary);text-decoration:none;">← Volver al blog</a>
            </div>
        </div>
    </article>"""

    html = render_blog_layout(
        client, content,
        title=post.titulo,
        meta_description=post.meta_description or "",
        og_image=post.imagen_destacada_url or "",
        canonical_url=canonical_url,
        schema_json_ld=schema,
        article_date=post.fecha_publicado,
    )
    return HTMLResponse(content=html)


def _build_seo_config(client: Client):
    """Construye ClientSEOConfig desde el modelo de cliente."""
    from core.seo_engine import ClientSEOConfig
    
    return ClientSEOConfig(
        integration_level=client.seo_integration_level or "external",
        canonical_domain=client.seo_canonical_domain or "",
        blog_base_url=client.seo_blog_base_url or f"https://blogengine.app/b/{client.blog_slug}",
        proxy_path=client.seo_proxy_path or "/blog",
        organization_name=client.nombre,
        organization_logo=(client.blog_design or {}).get("logo_url", ""),
        organization_url=client.sitio_web,
        social_profiles=client.seo_social_profiles or [],
        google_analytics_id=client.seo_google_analytics_id or "",
        default_author=client.seo_default_author or "",
        language=client.idioma or "es",
        region="MX",
    )


async def _render_sitemap(client: Client, db: AsyncSession, base_path: str) -> Response:
    """Genera sitemap.xml con URLs canónicas correctas e image sitemap."""
    from core.seo_engine import SitemapGenerator, CanonicalURLBuilder
    
    result = await db.execute(
        select(BlogPost)
        .where(BlogPost.client_id == client.id, BlogPost.estado == "publicado")
        .order_by(desc(BlogPost.fecha_publicado))
    )
    posts = result.scalars().all()
    
    seo_config = _build_seo_config(client)
    blog_home_url = CanonicalURLBuilder.build_blog_home_url(seo_config)
    
    posts_data = [
        {
            "slug": p.slug,
            "title": p.titulo,
            "date": p.fecha_publicado or p.created_at,
            "image": p.imagen_destacada_url or "",
        }
        for p in posts
    ]

    xml = SitemapGenerator.generate(posts_data, blog_home_url, seo_config)
    return Response(content=xml, media_type="application/xml")


async def _render_rss(client: Client, db: AsyncSession, base_path: str) -> Response:
    """Genera feed RSS con URLs canónicas."""
    from core.seo_engine import CanonicalURLBuilder
    
    result = await db.execute(
        select(BlogPost)
        .where(BlogPost.client_id == client.id, BlogPost.estado == "publicado")
        .order_by(desc(BlogPost.fecha_publicado))
        .limit(20)
    )
    posts = result.scalars().all()
    
    seo_config = _build_seo_config(client)
    blog_home_url = CanonicalURLBuilder.build_blog_home_url(seo_config)

    items = []
    for post in posts:
        post_url = CanonicalURLBuilder.build_canonical_url(seo_config, post.slug)
        fecha = post.fecha_publicado or post.created_at
        pub_date = fecha.strftime("%a, %d %b %Y %H:%M:%S GMT") if fecha else ""
        items.append(f"""    <item>
      <title>{post.titulo}</title>
      <link>{post_url}</link>
      <description>{post.extracto or post.meta_description or ''}</description>
      <pubDate>{pub_date}</pubDate>
      <guid>{post_url}</guid>
    </item>""")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Blog | {client.nombre}</title>
    <link>{blog_home_url}</link>
    <description>{client.descripcion_negocio or f'Blog de {client.nombre}'}</description>
    <language>{client.idioma or 'es'}</language>
{chr(10).join(items)}
  </channel>
</rss>"""

    return Response(content=xml, media_type="application/rss+xml")
