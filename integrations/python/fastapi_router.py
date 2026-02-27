"""
BlogEngine FastAPI Router.

INSTALACIÓN:
    from blogengine_fastapi import router as blog_router
    app.include_router(blog_router, prefix="/blog")

.ENV:
    BLOGENGINE_SLUG=mi-empresa
"""
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response
from blogengine_client import BlogEngineClient, render_seo_meta, render_schema_article

router = APIRouter()

SLUG = os.environ.get("BLOGENGINE_SLUG", "")
API_URL = os.environ.get("BLOGENGINE_API_URL", "https://blogengine.app")
SITE_NAME = os.environ.get("SITE_NAME", "")
SITE_URL = os.environ.get("SITE_URL", "https://localhost")

client = BlogEngineClient(SLUG, API_URL)


def _layout(meta: str, schema: str, content: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
    {meta}
    {schema}
    <style>
        body {{ font-family: -apple-system, sans-serif; line-height:1.7; color:#1f2937; margin:0; }}
        .container {{ max-width:800px; margin:2rem auto; padding:0 1.5rem; }}
        a {{ color:#2563eb; }} .meta {{ color:#888; font-size:0.875rem; }}
    </style>
</head>
<body><div class="container">{content}</div></body>
</html>"""


@router.get("/", response_class=HTMLResponse)
async def blog_index():
    posts = await client.get_posts(limit=20)
    cards = ""
    for p in posts:
        f = (p.get("fecha_publicado") or "")[:10]
        cards += f'<article style="margin-bottom:2.5rem;padding-bottom:2.5rem;border-bottom:1px solid #eee;">'
        cards += f'<h2><a href="/blog/{p["slug"]}" style="color:inherit;text-decoration:none;">{p["titulo"]}</a></h2>'
        cards += f'<div class="meta">{f}</div><p>{p.get("extracto","")}</p>'
        cards += f'<a href="/blog/{p["slug"]}">Leer más →</a></article>'
    if not posts:
        cards = '<p style="text-align:center;color:#999;padding:4rem 0;">Próximamente.</p>'
    return _layout('<title>Blog</title>', '', f'<h1>Blog</h1>{cards}')


@router.get("/sitemap.xml")
async def blog_sitemap():
    posts = await client.get_posts(limit=100)
    base = f"{SITE_URL}/blog"
    xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    xml += f'<url><loc>{base}</loc><changefreq>daily</changefreq><priority>1.0</priority></url>'
    for p in posts:
        d = (p.get("fecha_publicado") or "")[:10]
        xml += f'<url><loc>{base}/{p["slug"]}</loc><lastmod>{d}</lastmod><priority>0.8</priority></url>'
    xml += '</urlset>'
    return Response(content=xml, media_type="application/xml")


@router.get("/{slug}", response_class=HTMLResponse)
async def blog_post(slug: str):
    post = await client.get_post(slug)
    if not post:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")
    canonical = f"{SITE_URL}/blog/{slug}"
    meta = render_seo_meta(post, canonical, SITE_NAME)
    schema = render_schema_article(post, canonical, SITE_NAME, SITE_URL)
    f = (post.get("fecha_publicado") or "")[:10]
    content = f'<article><h1>{post["titulo"]}</h1><div class="meta">{f}</div>'
    content += f'<div style="line-height:1.8;">{post.get("contenido_html","")}</div>'
    content += '<div style="margin-top:2rem;"><a href="/blog">← Volver</a></div></article>'
    return _layout(meta, schema, content)
