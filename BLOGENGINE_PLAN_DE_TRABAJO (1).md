# BlogEngine — Plan de Trabajo por Etapas

## Contexto del Proyecto

BlogEngine es una plataforma SaaS que genera artículos de blog SEO-optimizados con IA para múltiples clientes. El objetivo principal es **posicionar al cliente en Google** — no simplemente "generar contenido bonito". Cada artículo es una máquina de tráfico orgánico que envía link juice a las páginas de dinero del cliente.

**Stack:** Python 3.12 + FastAPI + SQLAlchemy async + SQLite (dev) / PostgreSQL (prod)
**IA:** DeepSeek V3.2 (generación barata) + Claude (revisión de calidad)
**Deploy:** Docker + Coolify

El proyecto ya tiene una estructura base con 42 archivos y ~5,800 líneas de código. Este plan organiza el trabajo restante para llevarlo a producción.

---

## ETAPA 1 — Infraestructura Base (Semana 1)

**Objetivo:** Que el servidor arranque, la BD funcione, y se pueda crear un cliente vía API.

### Tareas:

1. Revisar y corregir todos los modelos SQLAlchemy en `models/`:
   - `client.py` — tiene campos de blog (blog_slug, blog_domain, blog_design) y SEO (seo_integration_level, seo_canonical_domain, etc.)
   - `blog_post.py` — campos: titulo, slug, contenido_html, keyword_principal, keywords_secundarias, estado, seo score, costos
   - `seo_strategy.py` — modelos: MoneyPage, TopicCluster, SEOKeyword, SEOAuditLog
   - `social_post.py`, `ai_usage.py`
   - Verificar que todos los modelos se importan en `models/__init__.py`

2. Verificar que `models/base.py` funciona:
   - AsyncSession con aiosqlite para dev
   - Función `init_db()` que crea todas las tablas
   - `get_db()` como dependency de FastAPI

3. Verificar que `api/main.py` arranca:
   - Lifespan event que llama `init_db()`
   - Todos los routers incluidos correctamente
   - CORS configurado
   - Docs en `/docs`

4. Probar CRUD de clientes:
   - `POST /api/clients/` → crear cliente con blog_slug auto-generado
   - `GET /api/clients/` → listar
   - `GET /api/clients/{id}` → detalle

5. Crear script `scripts/seed_test_data.py` que cree:
   - 1 cliente de prueba (Raíz Rentable, inmobiliario)
   - 3 money pages (propiedades, contacto, WhatsApp)
   - Ejecutable con `make seed`

### Criterio de aceptación:
```bash
make install && make db-init && make seed && make dev
# → http://localhost:8000/docs funciona
# → GET /api/clients/ devuelve el cliente de prueba
```

---

## ETAPA 2 — Proveedores de IA + Router (Semana 1-2)

**Objetivo:** Poder llamar a DeepSeek y Claude desde la API, con routing inteligente y tracking de costos.

### Tareas:

1. Configurar proveedores en `core/ai_providers/`:
   - `base.py` — clase abstracta AIProvider, dataclass AIResponse (contenido, tokens, costo_usd, proveedor, modelo, exito, error)
   - `deepseek.py` — usa SDK de OpenAI apuntando a api.deepseek.com. Modelo: deepseek-chat. Precios: $0.28/$0.42 por 1M tokens
   - `claude.py` — usa SDK de Anthropic. Modelos: haiku, sonnet, opus con precios por tier

2. Implementar `core/ai_router.py`:
   - Mapeo de tareas a proveedores según `config.yaml`
   - Tareas: generacion_articulo, revision_editorial, copies_redes_sociales, estrategia_editorial
   - Fallback: si DeepSeek falla → Claude Haiku
   - Método `generate()` y `generate_direct()`

3. Implementar `core/cost_tracker.py`:
   - Registra cada llamada IA en tabla ai_usage
   - Consulta costos por cliente, mes, proveedor

4. Test manual:
   - Endpoint temporal `POST /api/test/ai` que reciba un prompt y devuelva respuesta con costos

### Criterio de aceptación:
```bash
# Con DEEPSEEK_API_KEY en .env:
curl -X POST localhost:8000/api/test/ai -d '{"prompt":"Hola mundo"}'
# → Devuelve respuesta de DeepSeek con tokens y costo
```

---

## ETAPA 3 — Motor SEO Strategy (Semana 2)

**Objetivo:** Poder registrar money pages de un cliente e investigar keywords con IA.

### Tareas:

1. Implementar API de money pages en `api/routes/seo.py`:
   - `POST /api/seo/{client_id}/money-pages` — registrar página de dinero (URL, título, tipo, anchor texts, prioridad)
   - `GET /api/seo/{client_id}/money-pages` — listar
   - `DELETE /api/seo/{client_id}/money-pages/{id}` — eliminar

2. Implementar keyword research en `core/seo_strategy.py`:
   - `KeywordStrategyPlanner.build_strategy_prompt()` — construye prompt para que la IA investigue keywords del nicho del cliente
   - La IA devuelve JSON con clusters temáticos + keywords priorizadas + calendario

3. Implementar endpoint de research:
   - `POST /api/seo/{client_id}/research` — llama a la IA, parsea JSON, guarda clusters y keywords en BD
   - Requiere que el cliente tenga al menos 1 money page registrada

4. Endpoints de consulta:
   - `GET /api/seo/{client_id}/keywords` — listar keywords (filtrable por estado, cluster)
   - `GET /api/seo/{client_id}/clusters` — listar clusters con progreso

5. Implementar `OnPageSEOOptimizer.audit()` en `core/seo_strategy.py`:
   - Recibe: titulo, meta_description, slug, contenido_html, keyword_principal, keywords_secundarias
   - Verifica 15 criterios SEO (keyword en título, density 1-2%, H2s, links, longitud, etc.)
   - Devuelve puntuación 0-100 + checks + problemas + sugerencias

### Criterio de aceptación:
```bash
# Crear money pages
POST /api/seo/1/money-pages → 201
# Investigar keywords
POST /api/seo/1/research → devuelve clusters + keywords
# Ver keywords generadas
GET /api/seo/1/keywords → lista de 20 keywords con prioridad y cluster
```

---

## ETAPA 4 — Content Engine SEO-First (Semana 2-3)

**Objetivo:** Generar artículos que pasen auditoría SEO automática con score >= 70/100.

### Tareas:

1. Implementar `SEOPromptBuilder` en `core/seo_strategy.py`:
   - `build_generation_prompt()` — prompt que OBLIGA a la IA a: poner keyword en título/primer párrafo/H2s, incluir money links, internal links, density 1-2%
   - `build_review_prompt()` — prompt de corrección basado en resultados de auditoría

2. Implementar pipeline completo en `core/content_engine.py`:
   - `generate_article()` — pipeline de 7 pasos:
     a. Obtener money pages del cliente (para inyectar links)
     b. Obtener posts existentes (para internal linking)
     c. Construir prompt SEO-first con `SEOPromptBuilder`
     d. Generar borrador con DeepSeek
     e. Auditar con `OnPageSEOOptimizer`
     f. Si score < 70 → enviar a corrección con Claude (máx 2 intentos)
     g. Inyectar money links + internal links que falten
   - `generate_for_keyword()` — toma keyword de la BD y llama a `generate_article()`
   - `generate_social_copies()` — genera copies para redes sociales

3. Endpoints de generación en `api/routes/seo.py`:
   - `POST /api/seo/{client_id}/generate/from-keyword` — genera desde keyword de la estrategia
   - `POST /api/seo/{client_id}/generate/direct` — genera con keyword directa
   - `POST /api/seo/{client_id}/generate/batch` — genera múltiples (las N keywords de mayor prioridad)

4. Endpoint de auditoría manual:
   - `POST /api/seo/{client_id}/audit/{post_id}` — ejecuta auditoría en post existente
   - `GET /api/seo/{client_id}/audits` — listar auditorías

### Criterio de aceptación:
```bash
# Generar artículo para una keyword
POST /api/seo/1/generate/direct
{"keyword": "comprar casa en cdmx", "keywords_secundarias": ["crédito hipotecario", "enganche"]}
# → Devuelve: blog_post_id, seo_score >= 70, money links presentes en HTML
```

---

## ETAPA 5 — Blog Renderer Público (Semana 3)

**Objetivo:** Que los blogs se vean en la web con SEO completo (schema, canonical, OG, sitemap).

### Tareas:

1. Implementar `core/blog_renderer.py`:
   - Resolver cliente por slug: `blogengine.app/b/{slug}`
   - Resolver cliente por dominio personalizado: `blog.cliente.com` (Host header)
   - HTML server-side rendered con diseño personalizable por cliente (colores, logo, font)

2. Endpoints públicos:
   - `GET /b/{slug}` → home del blog (lista de artículos)
   - `GET /b/{slug}/{post_slug}` → artículo individual
   - `GET /b/{slug}/sitemap.xml` → sitemap con image sitemap
   - `GET /b/{slug}/rss.xml` → feed RSS

3. SEO en cada página:
   - Meta tags completos (OG, Twitter Cards, canonical) usando `core/seo_engine.py`
   - Schema.org JSON-LD (Article, BreadcrumbList, Organization, CollectionPage)
   - Canonical URL según nivel de integración del cliente (subdirectory/subdomain/external)
   - Google Analytics si está configurado
   - Internal links automáticos entre artículos del mismo blog
   - Artículos relacionados al final de cada post
   - Tiempo de lectura + conteo de palabras

4. API pública JSON:
   - `GET /api/public/{slug}/posts` → JSON de posts (para integraciones JS)
   - `GET /api/public/{slug}/posts/{post_slug}` → detalle en JSON

5. Script embebible:
   - `GET /embed/{slug}.js` → widget JS para pegar en cualquier sitio

### Criterio de aceptación:
```bash
# Ver blog del cliente de prueba
GET /b/raiz-rentable → HTML con artículos, schema markup, OG tags
# Ver artículo
GET /b/raiz-rentable/comprar-casa-cdmx → artículo con SEO completo
# Sitemap
GET /b/raiz-rentable/sitemap.xml → XML válido con URLs canónicas
```

---

## ETAPA 6 — Publicación + Distribución (Semana 3-4)

**Objetivo:** Publicar artículos y distribuir a redes sociales.

### Tareas:

1. Endpoints de publicación en `api/routes/publish.py`:
   - `POST /api/publish/{post_id}/go-live` — cambia estado a "publicado", genera URL
   - `POST /api/publish/{post_id}/unpublish` — despublica
   - `POST /api/publish/{post_id}/distribute` — genera copies y distribuye a redes
   - `POST /api/publish/{post_id}/full-pipeline` — publica + distribuye

2. Ping a buscadores:
   - `POST /api/seo/{client_id}/ping-google` — notifica sitemap a Google y Bing

3. Diagnóstico SEO:
   - `GET /api/seo/{client_id}/diagnostic` — puntuación global, stats, problemas, recomendaciones

### Criterio de aceptación:
```bash
POST /api/publish/1/go-live → estado "publicado", URL generada
GET /b/raiz-rentable → el artículo aparece en la lista
```

---

## ETAPA 7 — Integraciones (Semana 4)

**Objetivo:** Conectar BlogEngine con CUALQUIER sitio del cliente (WordPress, Laravel, HTML, etc.)

### Tareas:

1. API de integraciones en `api/routes/integrations.py`:
   - `GET /api/integrations/{client_id}/options` — lista todas las opciones con comparativa SEO
   - `POST /api/integrations/{client_id}/setup` — genera instrucciones personalizadas por tecnología

2. Probar cada integración:
   - WordPress: plugin en `integrations/wordpress/blogengine-connector.php`
   - Laravel: controller en `integrations/laravel/BlogEngineController.php` + vistas Blade
   - Python: client universal en `integrations/python/blogengine_client.py` + blueprints Flask/Django/FastAPI
   - HTML estático: generador en `integrations/html-static/generate_static.py`
   - Cloudflare Worker: `integrations/cloudflare-worker/worker.js`
   - Configs de proxy: Nginx, Apache, Netlify

3. Documentar cada integración con pasos exactos de instalación.

### Criterio de aceptación:
```bash
POST /api/integrations/1/setup {"tecnologia": "wordpress"}
# → Devuelve pasos personalizados con el slug del cliente
POST /api/integrations/1/setup {"tecnologia": "html"}
# → Devuelve comando exacto de generate_static.py
```

---

## ETAPA 8 — Dashboard Admin (Semana 4-5)

**Objetivo:** UI web para gestionar clientes, ver artículos, aprobar contenido.

### Tareas:

1. Dashboard con Jinja2 + HTMX + TailwindCSS (o Alpine.js):
   - `/admin/` → Dashboard principal con stats globales
   - `/admin/clients/` → Lista de clientes con puntuación SEO
   - `/admin/clients/{id}/` → Detalle de cliente: money pages, keywords, posts, auditorías
   - `/admin/posts/` → Lista de posts con filtros (estado, cliente, SEO score)
   - `/admin/posts/{id}/` → Preview del artículo con resultado de auditoría SEO
   - `/admin/posts/{id}/approve` → Aprobar/rechazar con un clic

2. Flujo de aprobación:
   - Lista de posts "en_revision" → botón aprobar → cambia a "aprobado"
   - Botón publicar → go-live + ping Google
   - Botón regenerar → vuelve a generar con la misma keyword

3. Vista de diagnóstico SEO por cliente:
   - Puntuación global
   - Keywords con posición actual
   - Progreso de clusters
   - Costos del mes

### Criterio de aceptación:
```
Abrir /admin/ → ver dashboard con clientes y posts
Aprobar un post → se publica y aparece en el blog
```

---

## ETAPA 9 — Automatización con Celery (Semana 5-6)

**Objetivo:** Generación y publicación automática según calendario.

### Tareas:

1. Configurar Celery + Redis:
   - Worker en `docker-compose.yml`
   - Beat scheduler para tareas periódicas

2. Tareas programadas:
   - `generate_scheduled_posts` — cada día revisa qué clientes tienen posts programados y genera
   - `auto_publish` — publica posts aprobados cuando llega su fecha_programada
   - `distribute_to_social` — distribuye a redes sociales X horas después de publicar
   - `ping_search_engines` — ping semanal a Google/Bing con sitemaps actualizados
   - `update_keyword_positions` — (futuro) trackear posiciones en Google con API de Search Console

3. Calendario editorial:
   - `POST /api/calendar/{client_id}/generate` — IA genera calendario mensual basado en keywords pendientes
   - `GET /api/calendar/{client_id}/` — ver calendario del mes

### Criterio de aceptación:
```bash
docker-compose up → worker y beat arrancan
# Un post con fecha_programada=mañana se publica automáticamente al día siguiente
```

---

## ETAPA 10 — Billing con Stripe (Semana 6)

**Objetivo:** Cobrar a los clientes por el servicio.

### Tareas:

1. Integrar Stripe:
   - Crear productos/precios en Stripe para cada plan (free, starter, pro, agency)
   - Webhook de Stripe para gestionar suscripciones
   - Al crear cliente → crear customer en Stripe
   - Al cambiar plan → actualizar suscripción

2. Limitar features por plan:
   - FREE: 2 artículos/mes, sin revisión editorial, sin redes sociales
   - STARTER: 8 artículos/mes, revisión con Haiku, 2 redes
   - PRO: 20 artículos/mes, revisión con Sonnet, todas las redes
   - AGENCY: ilimitado, todo incluido

3. Dashboard de billing:
   - `/admin/billing/` → ingresos por mes, clientes por plan
   - Alertas cuando un cliente se acerca al límite de su plan

### Criterio de aceptación:
```
Cliente en plan FREE intenta generar artículo #3 → error con mensaje de upgrade
Webhook de Stripe cambia plan → límites actualizados
```

---

## Notas Técnicas Importantes

### Base de datos
- Desarrollo: SQLite con aiosqlite
- Producción: PostgreSQL con asyncpg
- Migraciones: Alembic (configurar en etapa 1)

### Variables de entorno requeridas
```
DEEPSEEK_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
FERNET_KEY=... (para encriptar credenciales)
DATABASE_URL=sqlite+aiosqlite:///./blogengine.db
REDIS_URL=redis://localhost:6379 (para Celery)
STRIPE_SECRET_KEY=sk_... (etapa 10)
```

### Estructura de archivos clave
```
blogengine/
├── core/
│   ├── ai_router.py           # Enruta tareas a DeepSeek o Claude
│   ├── content_engine.py       # Pipeline SEO-first de generación
│   ├── seo_engine.py           # Schema, meta tags, canonical, sitemap
│   ├── seo_strategy.py         # Keyword research, auditoría on-page
│   ├── cost_tracker.py         # Tracking de costos IA
│   └── blog_renderer.py        # Renderiza blogs públicos
├── models/
│   ├── client.py               # Cliente multi-tenant
│   ├── blog_post.py            # Artículos
│   ├── seo_strategy.py         # MoneyPage, TopicCluster, SEOKeyword, SEOAuditLog
│   ├── social_post.py          # Posts de redes sociales
│   └── ai_usage.py             # Uso de IA
├── api/routes/
│   ├── seo.py                  # API principal de SEO
│   ├── clients.py              # CRUD clientes
│   ├── posts.py                # Gestión posts
│   ├── publish.py              # Publicación
│   └── integrations.py         # Configuración de integraciones
└── integrations/               # Plugins/conectores por tecnología
```

### Principio #1 del proyecto
**El SEO del cliente es la prioridad.** Todo lo demás es secundario. Si un artículo no pasa la auditoría SEO (score < 70/100), no se publica. Si un artículo no tiene money links al negocio del cliente, no está cumpliendo su función.
