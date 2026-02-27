# 🚀 BlogEngine — SEO-First Content Platform

Plataforma que **posiciona a tus clientes en Google** generando contenido SEO-optimizado con IA.

No es "un blog bonito". Es una máquina de tráfico orgánico.

## Filosofía

```
Cada artículo existe para POSICIONAR AL CLIENTE en Google.
Cada link dentro del artículo envía tráfico al NEGOCIO del cliente.
```

## Flujo de trabajo SEO-first

```
1. MONEY PAGES    → ¿Dónde convierte el cliente? (servicios, contacto, WhatsApp)
2. INVESTIGAR     → ¿Qué keywords tiene sentido atacar?
3. PLANIFICAR     → Organizar en clusters temáticos (silos)
4. GENERAR        → IA crea artículo optimizado para UNA keyword
5. AUDITAR        → Verifica 15+ criterios SEO on-page
6. CORREGIR       → Si no pasa auditoría (< 70/100), IA corrige automáticamente
7. ENLAZAR        → Inyecta money links + internal links
8. PUBLICAR       → Solo si SEO score >= 70/100
9. DISTRIBUIR     → Redes sociales para generar señales y tráfico
10. INDEXAR       → Ping a Google/Bing
```

## Inicio rápido

```bash
python -m venv .venv && source .venv/bin/activate
make install && make setup-env
# Editar .env con API keys (DeepSeek + Anthropic mínimo)
make fernet-key  # Copiar a .env
make db-init && make dev
# → http://localhost:8000/docs
```

## Flujo completo de un cliente

```bash
# 1. Crear cliente
POST /api/clients/
{ "nombre": "Raíz Rentable", "industria": "inmobiliario", "sitio_web": "https://raizrentable.com" }

# 2. Registrar sus páginas de dinero (OBLIGATORIO antes de generar)
POST /api/seo/1/money-pages
{ "url": "https://raizrentable.com/propiedades", "titulo": "Propiedades disponibles", "anchor_texts": ["ver propiedades", "conoce nuestro catálogo"], "prioridad": 5 }
{ "url": "https://wa.me/5215512345678", "titulo": "WhatsApp", "tipo": "whatsapp", "anchor_texts": ["contáctanos por WhatsApp"], "prioridad": 4 }

# 3. IA investiga keywords del nicho
POST /api/seo/1/research?num_keywords=20
# → Genera clusters temáticos + keywords priorizadas + calendario

# 4. Ver keywords generadas
GET /api/seo/1/keywords
GET /api/seo/1/clusters

# 5. Generar artículo desde una keyword de la estrategia
POST /api/seo/1/generate/from-keyword
{ "keyword_id": 7 }
# → Genera, audita, corrige, inyecta money links, devuelve score SEO

# 6. O generar batch (las 4 keywords de mayor prioridad)
POST /api/seo/1/generate/batch?cantidad=4

# 7. Publicar
POST /api/publish/{post_id}/go-live

# 8. Distribuir a redes sociales
POST /api/publish/{post_id}/distribute

# 9. Notificar a Google
POST /api/seo/1/ping-google

# 10. Diagnóstico SEO completo
GET /api/seo/1/diagnostic
```

## Qué hace CADA artículo generado

| Criterio SEO | Qué hace BlogEngine |
|---|---|
| Keyword en título | Primeras 5 palabras, < 60 chars |
| Keyword en meta description | Con CTA, 120-155 chars |
| Keyword en primer párrafo | Primeras 50 palabras |
| Keyword density | 1-2% (natural, no forzado) |
| Estructura H2/H3 | Mín 4 secciones, keywords en H2s |
| Money links | 1-2 links a páginas de servicio del cliente |
| Internal links | 2-3 links a otros artículos del blog |
| Longitud | 800-1500 palabras |
| Schema markup | Article + BreadcrumbList + Organization |
| Open Graph | Título, descripción, imagen |
| Canonical URL | Apunta al dominio del cliente |
| Sitemap | Automático con image sitemap |

## Auditoría SEO automática

Cada artículo se audita con 15+ criterios antes de publicarse.
Score mínimo: **70/100**. Si no pasa → Claude lo corrige automáticamente.

## Estructura del proyecto

```
blogengine/
├── core/
│   ├── ai_router.py           # Enruta DeepSeek (volumen) ↔ Claude (calidad)
│   ├── content_engine.py       # Pipeline SEO-first de generación
│   ├── seo_engine.py           # Schema, meta tags, canonical, sitemap
│   ├── seo_strategy.py         # Keyword research, auditoría on-page, prompts SEO
│   ├── cost_tracker.py         # Tracking de costos por llamada IA
│   └── blog_renderer.py        # Renderiza blogs con SEO completo
├── models/
│   ├── client.py               # Cliente (tenant)
│   ├── blog_post.py            # Artículo de blog
│   ├── seo_strategy.py         # MoneyPage, TopicCluster, SEOKeyword, SEOAuditLog
│   ├── social_post.py          # Publicación en redes
│   └── ai_usage.py             # Tracking de uso de IA
├── api/routes/
│   ├── seo.py                  # ★ API principal: money pages, research, generate, audit
│   ├── clients.py              # CRUD clientes
│   ├── posts.py                # Gestión de posts
│   └── publish.py              # Publicación + distribución social
└── prompts/                    # Prompts por industria
```

## Estrategia de IA dual

| Tarea | Proveedor | Costo |
|-------|-----------|-------|
| Generación de artículo | DeepSeek V3.2 | ~$0.002/artículo |
| Corrección SEO | Claude Haiku | ~$0.01/artículo |
| Estrategia de keywords | Claude Sonnet (PRO) | ~$0.02/investigación |
| Copies redes sociales | DeepSeek V3.2 | ~$0.001/red |

**20 clientes × 4 artículos/mes ≈ $0.87 USD/mes en IA.**

---

**BlogEngine** — SEO del cliente primero, siempre.
