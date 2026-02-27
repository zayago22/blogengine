"""
BlogEngine Django Integration.

INSTALACIÓN:
1. Copiar esta carpeta a tu proyecto Django
2. Agregar 'blogengine' a INSTALLED_APPS
3. En urls.py principal:
   path('blog/', include('blogengine.urls')),
4. En settings.py:
   BLOGENGINE_SLUG = 'mi-empresa'
   BLOGENGINE_API_URL = 'https://blogengine.app'  # opcional
"""

# === views.py ===

from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.conf import settings
import httpx
import json
from functools import lru_cache
import time

_cache = {}
CACHE_TTL = getattr(settings, 'BLOGENGINE_CACHE_TTL', 3600)
API_URL = getattr(settings, 'BLOGENGINE_API_URL', 'https://blogengine.app')
SLUG = getattr(settings, 'BLOGENGINE_SLUG', '')


def _fetch(endpoint):
    """Fetch con cache simple."""
    key = endpoint
    entry = _cache.get(key)
    if entry and time.time() - entry['t'] < CACHE_TTL:
        return entry['d']
    try:
        r = httpx.get(f"{API_URL}{endpoint}", timeout=10, headers={"Accept": "application/json"})
        if r.status_code == 200:
            data = r.json()
            _cache[key] = {'d': data, 't': time.time()}
            return data
        elif r.status_code == 404:
            return None
    except Exception:
        pass
    return None


def blog_index(request):
    """GET /blog/ → Lista de artículos."""
    posts = _fetch(f"/api/public/{SLUG}/posts?limit=20") or []
    # Si tienes templates Django, usa render():
    # return render(request, 'blogengine/index.html', {'posts': posts})
    
    # Template inline (reemplaza con tu propio template)
    cards = ""
    for p in posts:
        f = (p.get('fecha_publicado') or '')[:10]
        cards += f"""
        <article style="margin-bottom:2.5rem;padding-bottom:2.5rem;border-bottom:1px solid #eee;">
            <h2><a href="/blog/{p['slug']}" style="color:inherit;text-decoration:none;">{p['titulo']}</a></h2>
            <div style="color:#888;font-size:0.875rem;">{f}</div>
            <p>{p.get('extracto', '')}</p>
            <a href="/blog/{p['slug']}" style="color:#2563eb;">Leer más →</a>
        </article>"""
    
    html = f"""<!DOCTYPE html><html lang="es"><head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
    <title>Blog</title>
    <style>body{{font-family:-apple-system,sans-serif;line-height:1.7;color:#1f2937;margin:0;}}
    .c{{max-width:800px;margin:2rem auto;padding:0 1.5rem;}}</style>
    </head><body><div class="c"><h1>Blog</h1>{cards}</div></body></html>"""
    return HttpResponse(html)


def blog_post(request, slug):
    """GET /blog/<slug>/ → Artículo individual."""
    post = _fetch(f"/api/public/{SLUG}/posts/{slug}")
    if not post:
        raise Http404("Artículo no encontrado")
    
    site_name = getattr(settings, 'SITE_NAME', '')
    canonical = request.build_absolute_uri()
    title = post.get('titulo', '')
    desc = post.get('meta_description', '')
    image = post.get('imagen_destacada_url', '')
    fecha = (post.get('fecha_publicado') or '')[:10]
    
    schema = json.dumps({
        "@context": "https://schema.org", "@type": "Article",
        "headline": title, "description": desc,
        "url": canonical, "datePublished": post.get('fecha_publicado', ''),
        "publisher": {"@type": "Organization", "name": site_name},
    }, ensure_ascii=False)
    
    html = f"""<!DOCTYPE html><html lang="es"><head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
    <title>{title} | {site_name}</title>
    <meta name="description" content="{desc}">
    <link rel="canonical" href="{canonical}">
    <meta property="og:title" content="{title}"><meta property="og:description" content="{desc}">
    <meta property="og:url" content="{canonical}"><meta property="og:type" content="article">
    {'<meta property="og:image" content="' + image + '">' if image else ''}
    <script type="application/ld+json">{schema}</script>
    <style>body{{font-family:-apple-system,sans-serif;line-height:1.7;color:#1f2937;margin:0;}}
    .c{{max-width:800px;margin:2rem auto;padding:0 1.5rem;}} a{{color:#2563eb;}}</style>
    </head><body><div class="c">
    <article><h1>{title}</h1><div style="color:#888;margin-bottom:2rem;">{fecha}</div>
    <div style="line-height:1.8;">{post.get('contenido_html', '')}</div>
    <div style="margin-top:2rem;"><a href="/blog/">← Volver al blog</a></div>
    </article></div></body></html>"""
    return HttpResponse(html)


def blog_sitemap(request):
    """GET /blog/sitemap.xml"""
    posts = _fetch(f"/api/public/{SLUG}/posts?limit=100") or []
    base = request.build_absolute_uri('/blog')
    xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    xml += f'<url><loc>{base}</loc><changefreq>daily</changefreq><priority>1.0</priority></url>'
    for p in posts:
        d = (p.get('fecha_publicado') or '')[:10]
        xml += f'<url><loc>{base}/{p["slug"]}</loc><lastmod>{d}</lastmod><priority>0.8</priority></url>'
    xml += '</urlset>'
    return HttpResponse(xml, content_type='application/xml')


# === urls.py ===
# from django.urls import path
# from . import views
# urlpatterns = [
#     path('', views.blog_index, name='blog_index'),
#     path('sitemap.xml', views.blog_sitemap, name='blog_sitemap'),
#     path('<slug:slug>/', views.blog_post, name='blog_post'),
# ]
