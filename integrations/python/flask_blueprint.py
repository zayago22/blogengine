"""
BlogEngine Flask Blueprint.

INSTALACIÓN:
    from blogengine_flask import blogengine_bp
    app.register_blueprint(blogengine_bp, url_prefix='/blog')

.ENV o config:
    BLOGENGINE_SLUG=mi-empresa
"""
from flask import Blueprint, render_template_string, abort, Response, current_app
from blogengine_client import BlogEngineClient, render_seo_meta, render_schema_article
import os

blogengine_bp = Blueprint('blogengine', __name__)

def _get_client() -> BlogEngineClient:
    slug = os.environ.get('BLOGENGINE_SLUG', current_app.config.get('BLOGENGINE_SLUG', ''))
    url = os.environ.get('BLOGENGINE_API_URL', 'https://blogengine.app')
    return BlogEngineClient(slug, url)

# ─── Templates inline (o usa tus propios templates Jinja2) ───

LAYOUT = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {{ meta_tags | safe }}
    {{ schema | safe }}
    <style>
        body { font-family: -apple-system, sans-serif; line-height: 1.7; color: #1f2937; margin: 0; }
        .container { max-width: 800px; margin: 2rem auto; padding: 0 1.5rem; }
        a { color: #2563eb; }
        .meta { color: #888; font-size: 0.875rem; margin-bottom: 1rem; }
    </style>
</head>
<body>
    <div class="container">{{ content | safe }}</div>
</body>
</html>"""


@blogengine_bp.route('/')
def blog_index():
    client = _get_client()
    posts = client.get_posts_sync(limit=20)
    
    cards = ""
    for p in posts:
        fecha = p.get('fecha_publicado', '')[:10] if p.get('fecha_publicado') else ''
        cards += f"""
        <article style="margin-bottom:2.5rem;padding-bottom:2.5rem;border-bottom:1px solid #eee;">
            <h2><a href="/blog/{p['slug']}" style="color:inherit;text-decoration:none;">{p['titulo']}</a></h2>
            <div class="meta">{fecha}</div>
            <p>{p.get('extracto', '')}</p>
            <a href="/blog/{p['slug']}">Leer más →</a>
        </article>"""
    
    if not posts:
        cards = '<p style="text-align:center;color:#999;padding:4rem 0;">Próximamente.</p>'
    
    content = f"<h1>Blog</h1>{cards}"
    meta = '<title>Blog</title><meta name="description" content="Blog">'
    return render_template_string(LAYOUT, meta_tags=meta, schema="", content=content)


@blogengine_bp.route('/<slug>')
def blog_post(slug):
    client = _get_client()
    post = client.get_post_sync(slug)
    if not post:
        abort(404)
    
    canonical = f"https://{os.environ.get('SERVER_NAME', 'localhost')}/blog/{slug}"
    site_name = os.environ.get('SITE_NAME', '')
    
    meta = render_seo_meta(post, canonical, site_name)
    schema = render_schema_article(post, canonical, site_name, f"https://{os.environ.get('SERVER_NAME', '')}")
    
    fecha = post.get('fecha_publicado', '')[:10] if post.get('fecha_publicado') else ''
    content = f"""
    <article>
        <h1>{post['titulo']}</h1>
        <div class="meta">{fecha}</div>
        <div style="line-height:1.8;">{post.get('contenido_html', '')}</div>
        <div style="margin-top:2rem;"><a href="/blog">← Volver al blog</a></div>
    </article>"""
    
    return render_template_string(LAYOUT, meta_tags=meta, schema=schema, content=content)


@blogengine_bp.route('/sitemap.xml')
def blog_sitemap():
    client = _get_client()
    posts = client.get_posts_sync(limit=100)
    base = f"https://{os.environ.get('SERVER_NAME', 'localhost')}/blog"
    
    xml = '<?xml version="1.0" encoding="UTF-8"?>'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    xml += f'<url><loc>{base}</loc><changefreq>daily</changefreq><priority>1.0</priority></url>'
    for p in (posts or []):
        d = p.get('fecha_publicado', '')[:10]
        xml += f'<url><loc>{base}/{p["slug"]}</loc><lastmod>{d}</lastmod><priority>0.8</priority></url>'
    xml += '</urlset>'
    return Response(xml, mimetype='application/xml')
