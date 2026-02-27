# BlogEngine

Plataforma SaaS que genera artículos de blog SEO-optimizados con IA para múltiples clientes. El SEO del cliente es la prioridad #1.

## Stack
- Python 3.12 + FastAPI + SQLAlchemy async + aiosqlite (dev) / asyncpg (prod)
- IA: DeepSeek V3.2 (genera barato) + Claude Anthropic (revisa calidad)
- Deploy: Docker + Coolify

## Arquitectura
```
api/main.py              → FastAPI app, lifespan init_db()
api/routes/seo.py        → API principal: money pages, research, generate, audit
api/routes/clients.py    → CRUD clientes
api/routes/posts.py      → Gestión posts
api/routes/publish.py    → Publicación + distribución
api/routes/integrations.py → Config integración por tecnología
core/content_engine.py   → Pipeline SEO-first de generación (7 pasos)
core/seo_strategy.py     → Keyword research, auditoría on-page (15 criterios), prompts SEO
core/seo_engine.py       → Schema.org, meta tags, canonical, sitemap
core/ai_router.py        → Enruta tareas a DeepSeek o Claude según plan
core/ai_providers/       → base.py (abstracto), deepseek.py, claude.py
core/blog_renderer.py    → Blog público SSR con SEO completo
core/cost_tracker.py     → Tracking costos por llamada IA
models/client.py         → Cliente multi-tenant con campos SEO
models/blog_post.py      → Artículo con keyword, score, costos
models/seo_strategy.py   → MoneyPage, TopicCluster, SEOKeyword, SEOAuditLog
models/base.py           → AsyncSession, init_db(), get_db()
integrations/            → Plugins: WordPress, Laravel, Django, Flask, FastAPI, HTML, Cloudflare
core/celery_app.py       → Configuración Celery + Redis + Beat schedule
core/tasks/generation.py → Tarea: generación automática diaria de artículos
core/tasks/publishing.py → Tarea: publicación programada cada hora
core/tasks/seo_ping.py   → Tarea: ping semanal a Google/Bing
core/tasks/calendar_gen.py → Tarea: calendario editorial mensual con IA
core/tasks/social.py     → Tarea: distribución a redes sociales cada 2h
api/routes/tasks.py      → Endpoints monitoreo/disparo de tareas Celery
api/routes/calendar.py   → Endpoints calendario editorial
models/calendar.py       → CalendarEntry (calendario editorial)
```

## Flujo principal
1. Crear cliente → registrar money pages (URLs donde convierte)
2. POST /api/seo/{id}/research → IA investiga keywords del nicho
3. POST /api/seo/{id}/generate/from-keyword → genera artículo SEO-first
4. Auditoría automática (score < 70 → Claude corrige)
5. Money links + internal links inyectados
6. Publicar → ping Google

## Reglas
- Cada artículo ataca UNA keyword principal
- keyword en título (inicio), primer párrafo, H2s, meta description, slug
- keyword density 1-2%
- Mínimo 2 money links al sitio del cliente por artículo
- Mínimo 2 internal links a otros posts del blog
- Score SEO mínimo para publicar: 70/100
- Base de datos: SQLAlchemy async, NO síncrono
- API: FastAPI con async/await
- Blog público: HTML server-side (NO SPA), Google debe ver HTML
- Celery: cada tarea usa run_async() para ejecutar código async desde Celery
- Celery: cada tarea crea su propia sesión de BD con AsyncSessionLocal
- Celery: si una tarea falla para un cliente, continúa con los demás (try/except individual)
- Redis requerido para Celery (incluido en docker-compose)
- Tareas periódicas: generación 6AM, publicación cada hora, ping lunes 8AM, social cada 2h, calendario día 1

## Comandos
```bash
make install    # pip install -r requirements.txt
make db-init    # crear tablas
make seed       # datos de prueba
make dev        # uvicorn api.main:app --reload --port 8000
make worker     # celery worker (procesa tareas)
make beat       # celery beat (programa tareas)
make celery     # worker + beat juntos
make flower     # monitor web de Celery en :5555
```

## Plan de trabajo
Ver BLOGENGINE_PLAN_DE_TRABAJO.md para las 10 etapas detalladas.
Ejecutar etapa por etapa, un archivo a la vez.
