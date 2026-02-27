# 🔌 BlogEngine — Integraciones

Cada cliente tiene su sitio en tecnología diferente.
BlogEngine se conecta con TODAS:

```
TECNOLOGÍA          INTEGRACIÓN              SEO RESULT
═══════════════════════════════════════════════════════
WordPress           Plugin PHP               ⭐⭐⭐⭐⭐ cliente.com/blog
Laravel             Package / Routes         ⭐⭐⭐⭐⭐ cliente.com/blog
Django/Flask/FastAPI Middleware / Blueprint    ⭐⭐⭐⭐⭐ cliente.com/blog
HTML estático       Static Site Generator     ⭐⭐⭐⭐⭐ cliente.com/blog/
                    + Cloudflare Worker       ⭐⭐⭐⭐⭐ cliente.com/blog
                    + Netlify Rewrite         ⭐⭐⭐⭐⭐ cliente.com/blog
Wix/Squarespace     Subdominio CNAME         ⭐⭐⭐⭐  blog.cliente.com
Cualquiera          JS Embed Widget          ⭐⭐⭐    (limitado SEO)
```

## Cómo funciona

Todas las integraciones hacen lo mismo:
1. El visitante entra a `cliente.com/blog`
2. La integración llama a la API de BlogEngine
3. BlogEngine devuelve el HTML/JSON del artículo
4. La integración lo renderiza DENTRO del sitio del cliente
5. Google ve `cliente.com/blog/articulo` → todo el SEO va al cliente ✅

## Instalación por tecnología

### WordPress → `integrations/wordpress/`
```
Copiar carpeta → wp-content/plugins/blogengine-connector/
Activar → Ajustes → BlogEngine → pegar slug
```

### Laravel → `integrations/laravel/`
```
Copiar BlogEngineController.php → app/Http/Controllers/
Copiar routes → routes/web.php
Copiar vista → resources/views/blogengine/
```

### Django → `integrations/python/django_app/`
```
Copiar app → proyecto/blogengine/
Agregar a INSTALLED_APPS
Agregar URL patterns
```

### Flask → `integrations/python/flask_blueprint.py`
```
Importar blueprint → registrar en app
```

### FastAPI → `integrations/python/fastapi_router.py`
```
Importar router → incluir en app
```

### HTML estático → `integrations/html-static/`
```
Opción A: Ejecutar generador → sube archivos .html al hosting
Opción B: Cloudflare Worker → proxy transparente
Opción C: Netlify → _redirects file
```
