#!/usr/bin/env python3
"""
BlogEngine Static Site Generator.

PARA CLIENTES CON SITIOS HTML ESTÁTICOS.

Genera archivos .html que se suben al hosting del cliente.
Google ve HTML puro → SEO perfecto ⭐⭐⭐⭐⭐

USO:
    python generate_static.py --slug mi-empresa --domain www.cliente.com --output ./blog

GENERA:
    blog/
    ├── index.html              ← Lista de artículos
    ├── mi-articulo.html        ← Artículo individual (uno por post)
    ├── sitemap.xml             ← Sitemap para Google
    └── rss.xml                 ← Feed RSS

DEPLOY:
    Subir la carpeta blog/ al hosting del cliente.
    FTP, rsync, GitHub Actions, lo que sea.

    Ejemplo con rsync:
        rsync -avz blog/ user@servidor:/var/www/cliente.com/blog/

    Ejemplo con FTP:
        lftp -u user,pass ftp://hosting.com -e "mirror -R blog/ /public_html/blog; quit"

AUTOMATIZACIÓN:
    Ejecutar cada vez que se publica un artículo nuevo.
    BlogEngine puede llamar un webhook que ejecute este script.

    Cron job (cada hora):
        0 * * * * cd /path/to && python generate_static.py --slug mi-empresa --output /var/www/blog/

pip install httpx jinja2
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import httpx
except ImportError:
    print("pip install httpx")
    sys.exit(1)


API_URL = os.environ.get("BLOGENGINE_API_URL", "https://blogengine.app")


def fetch(slug: str, endpoint: str):
    """Fetch data from BlogEngine API."""
    url = f"{API_URL}/api/public/{slug}/{endpoint}"
    try:
        r = httpx.get(url, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"  ❌ Error fetching {endpoint}: {e}")
    return None


def generate_html(post: dict, slug: str, domain: str, site_name: str, template: str = "") -> str:
    """Genera HTML completo de un artículo con SEO."""
    title = post.get("titulo", "")
    desc = post.get("meta_description", "")
    content = post.get("contenido_html", "")
    image = post.get("imagen_destacada_url", "")
    date = post.get("fecha_publicado", "")
    keyword = post.get("keyword", "")
    post_slug = post.get("slug", "")
    
    canonical = f"https://{domain}/blog/{post_slug}.html"
    date_display = date[:10] if date else ""

    schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": desc,
        "url": canonical,
        "datePublished": date,
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
        "publisher": {
            "@type": "Organization",
            "name": site_name,
            "url": f"https://{domain}",
        },
    }, ensure_ascii=False, indent=2)

    breadcrumb = json.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Inicio", "item": f"https://{domain}"},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": f"https://{domain}/blog/"},
            {"@type": "ListItem", "position": 3, "name": title, "item": canonical},
        ]
    }, ensure_ascii=False, indent=2)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <!-- SEO -->
    <title>{_esc(title)} | {_esc(site_name)}</title>
    <meta name="description" content="{_esc(desc)}">
    <link rel="canonical" href="{canonical}">
    {f'<meta name="keywords" content="{_esc(keyword)}">' if keyword else ''}
    <meta name="robots" content="index, follow, max-image-preview:large">
    
    <!-- Open Graph -->
    <meta property="og:title" content="{_esc(title)}">
    <meta property="og:description" content="{_esc(desc)}">
    <meta property="og:url" content="{canonical}">
    <meta property="og:type" content="article">
    <meta property="og:site_name" content="{_esc(site_name)}">
    {f'<meta property="og:image" content="{image}">' if image else ''}
    {f'<meta property="article:published_time" content="{date}">' if date else ''}
    
    <!-- Twitter -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{_esc(title)}">
    <meta name="twitter:description" content="{_esc(desc)}">
    
    <!-- Schema.org -->
    <script type="application/ld+json">
{schema}
    </script>
    <script type="application/ld+json">
{breadcrumb}
    </script>
    
    <!-- Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Inter', sans-serif; line-height: 1.7; color: #1f2937; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 0 1.5rem; }}
        header {{ border-bottom: 1px solid #e5e7eb; padding: 1rem 0; }}
        header .container {{ display: flex; justify-content: space-between; align-items: center; }}
        header a {{ color: #1f2937; text-decoration: none; font-weight: 500; }}
        header .logo {{ font-size: 1.25rem; font-weight: 700; color: #2563eb; }}
        article {{ padding: 3rem 0; }}
        article h1 {{ font-size: 2.25rem; line-height: 1.3; margin-bottom: 1rem; }}
        .meta {{ color: #6b7280; margin-bottom: 2rem; padding-bottom: 1.5rem; border-bottom: 1px solid #f3f4f6; }}
        .content h2 {{ font-size: 1.5rem; margin: 2rem 0 1rem; }}
        .content h3 {{ font-size: 1.25rem; margin: 1.5rem 0 0.75rem; }}
        .content p {{ margin-bottom: 1.25rem; }}
        .content ul, .content ol {{ margin: 1rem 0 1.25rem 1.5rem; }}
        .content li {{ margin-bottom: 0.5rem; }}
        .content a {{ color: #2563eb; }}
        .content img {{ max-width: 100%; height: auto; border-radius: 8px; margin: 1.5rem 0; }}
        .back {{ margin-top: 2rem; }}
        .back a {{ color: #2563eb; text-decoration: none; }}
        footer {{ border-top: 1px solid #e5e7eb; padding: 2rem 0; text-align: center; color: #9ca3af; font-size: 0.875rem; }}
    </style>
</head>
<body>
    <header>
        <div class="container" style="max-width:1100px;">
            <a href="https://{domain}" class="logo">{_esc(site_name)}</a>
            <nav>
                <a href="/blog/">Blog</a>
                <a href="https://{domain}" style="margin-left:1.5rem;">Sitio Web</a>
            </nav>
        </div>
    </header>
    
    <article>
        <div class="container">
            <h1>{_esc(title)}</h1>
            <div class="meta">{date_display}</div>
            <div class="content">
                {content}
            </div>
            <div class="back">
                <a href="/blog/">← Volver al blog</a>
            </div>
        </div>
    </article>
    
    <footer>
        <div class="container">
            <p>&copy; {_esc(site_name)}. Todos los derechos reservados.</p>
        </div>
    </footer>
</body>
</html>"""


def generate_index(posts: list, domain: str, site_name: str) -> str:
    """Genera index.html con la lista de artículos."""
    canonical = f"https://{domain}/blog/"
    
    cards = ""
    for p in posts:
        f = (p.get("fecha_publicado") or "")[:10]
        cards += f"""
        <article style="margin-bottom:2.5rem;padding-bottom:2.5rem;border-bottom:1px solid #eee;">
            <h2 style="margin-bottom:0.5rem;">
                <a href="{p['slug']}.html" style="color:inherit;text-decoration:none;">{_esc(p['titulo'])}</a>
            </h2>
            <div style="color:#888;font-size:0.875rem;margin-bottom:0.75rem;">{f}</div>
            <p>{_esc(p.get('extracto', ''))}</p>
            <a href="{p['slug']}.html" style="color:#2563eb;font-weight:500;">Leer más →</a>
        </article>"""
    
    if not posts:
        cards = '<p style="text-align:center;color:#999;padding:4rem 0;">Próximamente.</p>'

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blog | {_esc(site_name)}</title>
    <meta name="description" content="Blog de {_esc(site_name)}">
    <link rel="canonical" href="{canonical}">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ font-family:'Inter',sans-serif; line-height:1.7; color:#1f2937; }}
        .container {{ max-width:800px; margin:2rem auto; padding:0 1.5rem; }}
        a {{ color:#2563eb; }}
    </style>
</head>
<body>
    <div class="container">
        <h1 style="font-size:2rem;margin-bottom:2rem;">Blog</h1>
        {cards}
    </div>
</body>
</html>"""


def generate_sitemap(posts: list, domain: str) -> str:
    """Genera sitemap.xml."""
    base = f"https://{domain}/blog"
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
    xml += f'  <url><loc>{base}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>\n'
    for p in posts:
        d = (p.get("fecha_publicado") or "")[:10]
        img = p.get("imagen_destacada_url", "")
        xml += f'  <url><loc>{base}/{p["slug"]}.html</loc><lastmod>{d}</lastmod><priority>0.8</priority>'
        if img:
            xml += f'<image:image><image:loc>{img}</image:loc></image:image>'
        xml += '</url>\n'
    xml += '</urlset>'
    return xml


def _esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def main():
    parser = argparse.ArgumentParser(description="BlogEngine Static Site Generator")
    parser.add_argument("--slug", required=True, help="Blog slug en BlogEngine")
    parser.add_argument("--domain", required=True, help="Dominio del cliente (sin https://)")
    parser.add_argument("--site-name", default="", help="Nombre del sitio")
    parser.add_argument("--output", default="./blog", help="Carpeta de salida")
    parser.add_argument("--api-url", default=API_URL, help="URL de la API de BlogEngine")
    args = parser.parse_args()

    global API_URL
    API_URL = args.api_url
    site_name = args.site_name or args.domain
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    print(f"🚀 BlogEngine Static Generator")
    print(f"   Slug: {args.slug}")
    print(f"   Domain: {args.domain}")
    print(f"   Output: {output.resolve()}")
    print()

    # Fetch posts
    print("📥 Obteniendo artículos...")
    posts = fetch(args.slug, "posts?limit=100")
    if not posts:
        print("  ⚠️  No hay artículos publicados.")
        posts = []
    else:
        print(f"  ✅ {len(posts)} artículos encontrados")

    # Generate index
    print("📄 Generando index.html...")
    index_html = generate_index(posts, args.domain, site_name)
    (output / "index.html").write_text(index_html, encoding="utf-8")

    # Generate each post
    for i, p in enumerate(posts):
        slug = p["slug"]
        print(f"📄 [{i+1}/{len(posts)}] {slug}.html...")
        
        # Fetch full post
        full = fetch(args.slug, f"posts/{slug}")
        if full:
            html = generate_html(full, args.slug, args.domain, site_name)
            (output / f"{slug}.html").write_text(html, encoding="utf-8")
        else:
            print(f"  ⚠️  No se pudo obtener detalle de {slug}")

    # Sitemap
    print("🗺️  Generando sitemap.xml...")
    sitemap = generate_sitemap(posts, args.domain)
    (output / "sitemap.xml").write_text(sitemap, encoding="utf-8")

    print()
    print(f"✅ Listo! {len(posts) + 1} archivos generados en {output.resolve()}")
    print()
    print(f"SIGUIENTE PASO: Subir la carpeta al hosting del cliente:")
    print(f"  rsync -avz {output}/ user@servidor:/var/www/{args.domain}/blog/")
    print(f"  # o FTP, GitHub Actions, Netlify, etc.")


if __name__ == "__main__":
    main()
