"""
BlogEngine - API de Integraciones.
Auto-genera la configuración correcta según la tecnología del cliente.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.base import get_db
from models.client import Client

router = APIRouter()


class IntegrationRequest(BaseModel):
    """Solicitud de configuración de integración."""
    tecnologia: str = Field(
        ...,
        description="wordpress | laravel | django | flask | fastapi | html | netlify | cloudflare | nginx | apache"
    )
    dominio: Optional[str] = Field(None, description="Dominio del cliente (sin https://)")
    ruta_blog: str = Field(default="/blog", description="Ruta del blog en el sitio")


@router.post("/{client_id}/setup")
async def generar_integracion(
    client_id: int,
    data: IntegrationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Genera las instrucciones y código de integración
    personalizados para el cliente según su tecnología.
    """
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    slug = client.blog_slug or client.nombre.lower().replace(" ", "-")
    domain = data.dominio or (
        client.sitio_web.replace("https://", "").replace("http://", "").split("/")[0]
    )
    path = data.ruta_blog.strip("/")
    tech = data.tecnologia.lower()

    generators = {
        "wordpress": _gen_wordpress,
        "laravel": _gen_laravel,
        "django": _gen_django,
        "flask": _gen_flask,
        "fastapi": _gen_fastapi,
        "html": _gen_html_static,
        "netlify": _gen_netlify,
        "cloudflare": _gen_cloudflare,
        "nginx": _gen_nginx,
        "apache": _gen_apache,
    }

    gen = generators.get(tech)
    if not gen:
        raise HTTPException(
            status_code=400,
            detail=f"Tecnología '{tech}' no soportada. Opciones: {', '.join(generators.keys())}",
        )

    instructions = gen(slug, domain, path, client.nombre)

    return {
        "client": client.nombre,
        "tecnologia": tech,
        "blog_slug": slug,
        "dominio": domain,
        "blog_url": f"https://{domain}/{path}",
        "seo_level": instructions["seo_level"],
        "instrucciones": instructions,
    }


@router.get("/{client_id}/options")
async def listar_opciones_integracion(
    client_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Lista todas las opciones de integración disponibles con comparativa."""
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    return {
        "opciones": [
            {
                "tecnologia": "wordpress",
                "seo": "⭐⭐⭐⭐⭐",
                "dificultad": "Fácil",
                "descripcion": "Plugin PHP. Activar y configurar slug.",
                "resultado": "cliente.com/blog",
                "requiere": "Acceso admin WordPress",
            },
            {
                "tecnologia": "laravel",
                "seo": "⭐⭐⭐⭐⭐",
                "dificultad": "Fácil",
                "descripcion": "Controller + rutas + vistas Blade.",
                "resultado": "cliente.com/blog",
                "requiere": "Acceso al código Laravel",
            },
            {
                "tecnologia": "django",
                "seo": "⭐⭐⭐⭐⭐",
                "dificultad": "Fácil",
                "descripcion": "App Django con views y URLs.",
                "resultado": "cliente.com/blog",
                "requiere": "Acceso al código Django",
            },
            {
                "tecnologia": "flask",
                "seo": "⭐⭐⭐⭐⭐",
                "dificultad": "Fácil",
                "descripcion": "Blueprint Flask con templates.",
                "resultado": "cliente.com/blog",
                "requiere": "Acceso al código Flask",
            },
            {
                "tecnologia": "fastapi",
                "seo": "⭐⭐⭐⭐⭐",
                "dificultad": "Fácil",
                "descripcion": "Router FastAPI con HTML responses.",
                "resultado": "cliente.com/blog",
                "requiere": "Acceso al código FastAPI",
            },
            {
                "tecnologia": "nginx",
                "seo": "⭐⭐⭐⭐⭐",
                "dificultad": "Media",
                "descripcion": "Proxy inverso en Nginx.",
                "resultado": "cliente.com/blog",
                "requiere": "Acceso SSH al servidor",
            },
            {
                "tecnologia": "cloudflare",
                "seo": "⭐⭐⭐⭐⭐",
                "dificultad": "Media",
                "descripcion": "Worker que intercepta /blog. Funciona con CUALQUIER sitio.",
                "resultado": "cliente.com/blog",
                "requiere": "Dominio en Cloudflare (plan Free funciona)",
            },
            {
                "tecnologia": "html",
                "seo": "⭐⭐⭐⭐⭐",
                "dificultad": "Fácil",
                "descripcion": "Generador de archivos .html estáticos. Subir por FTP.",
                "resultado": "cliente.com/blog/articulo.html",
                "requiere": "Acceso FTP al hosting",
            },
            {
                "tecnologia": "netlify",
                "seo": "⭐⭐⭐⭐⭐",
                "dificultad": "Fácil",
                "descripcion": "Proxy via _redirects. Una línea de config.",
                "resultado": "cliente.com/blog",
                "requiere": "Sitio en Netlify",
            },
            {
                "tecnologia": "apache",
                "seo": "⭐⭐⭐⭐",
                "dificultad": "Media",
                "descripcion": ".htaccess con proxy. Si no funciona → usar HTML estático.",
                "resultado": "cliente.com/blog",
                "requiere": "mod_proxy habilitado (no siempre en hosting compartido)",
            },
        ],
        "recomendacion": "Si no sabes cuál elegir: Cloudflare Worker funciona con TODO.",
    }


# =========================================================================
# Generadores de instrucciones por tecnología
# =========================================================================

def _gen_wordpress(slug, domain, path, name):
    return {
        "seo_level": "⭐⭐⭐⭐⭐",
        "titulo": "WordPress — Plugin BlogEngine",
        "pasos": [
            f"1. Descargar plugin de integrations/wordpress/",
            f"2. Subir a wp-content/plugins/blogengine-connector/",
            f"3. Activar plugin en WordPress Admin → Plugins",
            f"4. Ir a Ajustes → BlogEngine",
            f"5. Pegar Blog Slug: {slug}",
            f"6. Ruta del blog: {path}",
            f"7. Guardar → El blog aparece en https://{domain}/{path}",
        ],
        "verificar": f"Visitar https://{domain}/{path} y verificar artículos.",
    }


def _gen_laravel(slug, domain, path, name):
    return {
        "seo_level": "⭐⭐⭐⭐⭐",
        "titulo": "Laravel — Controller + Routes",
        "pasos": [
            f"1. Copiar BlogEngineController.php → app/Http/Controllers/",
            f"2. Copiar vistas → resources/views/blogengine/",
            f"3. Agregar a routes/web.php:",
        ],
        "codigo_routes": f"""
// routes/web.php
use App\\Http\\Controllers\\BlogEngineController;

Route::get('/{path}', [BlogEngineController::class, 'index'])->name('blog.index');
Route::get('/{path}/sitemap.xml', [BlogEngineController::class, 'sitemap']);
Route::get('/{path}/rss.xml', [BlogEngineController::class, 'rss']);
Route::get('/{path}/{{slug}}', [BlogEngineController::class, 'show'])->name('blog.show');
""",
        "env": f"BLOGENGINE_SLUG={slug}\nBLOGENGINE_API_URL=https://blogengine.app",
    }


def _gen_django(slug, domain, path, name):
    return {
        "seo_level": "⭐⭐⭐⭐⭐",
        "titulo": "Django — App con Views",
        "pasos": [
            "1. Copiar django_views.py como app en tu proyecto",
            "2. Agregar 'blogengine' a INSTALLED_APPS",
            f"3. Agregar a urls.py: path('{path}/', include('blogengine.urls'))",
        ],
        "settings": f"BLOGENGINE_SLUG = '{slug}'\nBLOGENGINE_API_URL = 'https://blogengine.app'",
    }


def _gen_flask(slug, domain, path, name):
    return {
        "seo_level": "⭐⭐⭐⭐⭐",
        "titulo": "Flask — Blueprint",
        "pasos": [
            "1. Copiar flask_blueprint.py y blogengine_client.py al proyecto",
            "2. Registrar blueprint en tu app:",
        ],
        "codigo": f"""
from flask_blueprint import blogengine_bp
app.register_blueprint(blogengine_bp, url_prefix='/{path}')
""",
        "env": f"BLOGENGINE_SLUG={slug}",
    }


def _gen_fastapi(slug, domain, path, name):
    return {
        "seo_level": "⭐⭐⭐⭐⭐",
        "titulo": "FastAPI — Router",
        "pasos": [
            "1. Copiar fastapi_router.py y blogengine_client.py al proyecto",
            "2. Incluir router en tu app:",
        ],
        "codigo": f"""
from fastapi_router import router as blog_router
app.include_router(blog_router, prefix="/{path}")
""",
        "env": f"BLOGENGINE_SLUG={slug}\nSITE_URL=https://{domain}\nSITE_NAME={name}",
    }


def _gen_html_static(slug, domain, path, name):
    return {
        "seo_level": "⭐⭐⭐⭐⭐",
        "titulo": "HTML Estático — Generador de archivos .html",
        "descripcion": "Genera archivos .html que se suben al hosting por FTP. Google ve HTML puro.",
        "pasos": [
            "1. Instalar: pip install httpx",
            f"2. Ejecutar:",
        ],
        "comando": f"python generate_static.py --slug {slug} --domain {domain} --site-name \"{name}\" --output ./{path}",
        "pasos_cont": [
            f"3. Subir carpeta {path}/ al hosting del cliente por FTP:",
            f"   lftp -u user,pass ftp://hosting -e \"mirror -R {path}/ /public_html/{path}; quit\"",
            f"4. Verificar: https://{domain}/{path}/",
            "",
            "AUTOMATIZACIÓN: Ejecutar con cron cada hora:",
            f"   0 * * * * cd /path && python generate_static.py --slug {slug} --domain {domain} --output /var/www/{path}/",
        ],
    }


def _gen_cloudflare(slug, domain, path, name):
    return {
        "seo_level": "⭐⭐⭐⭐⭐",
        "titulo": "Cloudflare Worker — Funciona con CUALQUIER sitio",
        "descripcion": "Si el dominio usa Cloudflare, esto funciona sin importar la tecnología del sitio.",
        "pasos": [
            f"1. Ir a Cloudflare Dashboard → Workers & Pages → Create Worker",
            f"2. Pegar el código de integrations/cloudflare-worker/worker.js",
            f"3. En Settings → Variables, agregar:",
            f"   BLOGENGINE_SLUG = {slug}",
            f"   SITE_NAME = {name}",
            f"4. En Triggers → Routes, agregar:",
            f"   {domain}/{path}/*",
            f"5. Deploy → Listo. Blog en https://{domain}/{path}",
        ],
        "nota": "Funciona con el plan Free de Cloudflare. 100,000 requests/día gratis.",
    }


def _gen_netlify(slug, domain, path, name):
    return {
        "seo_level": "⭐⭐⭐⭐⭐",
        "titulo": "Netlify — Proxy con _redirects",
        "descripcion": "Una línea de configuración y listo.",
        "pasos": [
            "1. Crear archivo _redirects en la raíz del sitio (junto a index.html)",
            "2. Agregar estas líneas:",
        ],
        "archivo_redirects": f"""/{path}              https://blogengine.app/b/{slug}  200
/{path}/             https://blogengine.app/b/{slug}  200
/{path}/:slug        https://blogengine.app/b/{slug}/:slug  200
/{path}/sitemap.xml  https://blogengine.app/b/{slug}/sitemap.xml  200""",
        "pasos_cont": [
            "3. Commit y deploy → Listo",
            f"4. Verificar: https://{domain}/{path}",
        ],
    }


def _gen_nginx(slug, domain, path, name):
    return {
        "seo_level": "⭐⭐⭐⭐⭐",
        "titulo": "Nginx — Proxy Inverso",
        "pasos": [
            f"1. Editar la config de Nginx del dominio:",
            f"   sudo nano /etc/nginx/sites-available/{domain}",
            f"2. Agregar este bloque dentro de server {{ }}:",
        ],
        "codigo_nginx": f"""
location /{path} {{
    proxy_pass https://blogengine.app/b/{slug};
    proxy_set_header Host blogengine.app;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Original-Host $host;
    proxy_redirect off;
    proxy_cache_valid 200 1h;
}}""",
        "pasos_cont": [
            "3. Probar config: sudo nginx -t",
            "4. Recargar: sudo systemctl reload nginx",
            f"5. Verificar: https://{domain}/{path}",
        ],
    }


def _gen_apache(slug, domain, path, name):
    return {
        "seo_level": "⭐⭐⭐⭐",
        "titulo": "Apache — .htaccess con Proxy",
        "nota": "Requiere mod_proxy. Si no está habilitado, usar HTML estático.",
        "pasos": [
            f"1. Crear carpeta /{path} en el hosting",
            f"2. Crear .htaccess dentro de /{path}/ con:",
        ],
        "codigo_htaccess": f"""RewriteEngine On
RewriteRule ^$ https://blogengine.app/b/{slug} [P,L]
RewriteRule ^(.+)$ https://blogengine.app/b/{slug}/$1 [P,L]
ProxyPassReverse / https://blogengine.app/b/{slug}/""",
        "alternativa": f"Si mod_proxy no funciona, usar HTML estático: python generate_static.py --slug {slug} --domain {domain}",
    }
