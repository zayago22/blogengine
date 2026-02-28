"""
Dashboard Admin — rutas SSR con Jinja2 + HTMX.
"""
import logging
import re
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from starlette.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, delete
from models.base import get_db
from models.client import Client
from models.blog_post import BlogPost
from models.seo_strategy import MoneyPage, SEOKeyword, TopicCluster, SEOAuditLog
from models.ai_usage import AIUsage
from models.social_post import SocialPost
from models.calendar import CalendarEntry
from api.auth import require_auth, create_session_token, verify_session_token
from config import get_settings
from core.task_wrappers import task_research_keywords

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="templates")

# ============================================================
# AUTH: Login / Logout (sin require_auth)
# ============================================================

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Formulario de login."""
    return templates.TemplateResponse("admin/login.html", {
        "request": request,
        "error": None,
    })


@router.post("/login")
async def login_submit(request: Request):
    """Procesa el login. Si OK → cookie + redirect /admin/."""
    form = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "").strip()

    s = get_settings()
    if username == s.admin_user and password == s.admin_password:
        token = create_session_token()
        response = RedirectResponse(url="/admin/", status_code=303)
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 7,  # 7 días
        )
        logger.info(f"[Auth] Login exitoso: {username}")
        return response

    logger.warning(f"[Auth] Login fallido: {username}")
    return templates.TemplateResponse("admin/login.html", {
        "request": request,
        "error": "Credenciales incorrectas",
    }, status_code=401)


@router.get("/logout")
async def logout():
    """Cierra sesión borrando la cookie."""
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie("session_token")
    return response


# ============================================================
# DASHBOARD (rutas protegidas)
# ============================================================

@router.get("/", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
async def dashboard_home(request: Request, db: AsyncSession = Depends(get_db)):
    """Dashboard principal con stats."""
    # Stats generales
    total_clients = (await db.execute(select(func.count(Client.id)))).scalar() or 0
    total_posts = (await db.execute(select(func.count(BlogPost.id)))).scalar() or 0
    published_posts = (await db.execute(
        select(func.count(BlogPost.id)).where(BlogPost.estado == "publicado")
    )).scalar() or 0
    pending_posts = (await db.execute(
        select(func.count(BlogPost.id)).where(BlogPost.estado == "en_revision")
    )).scalar() or 0

    # Costo IA total
    costo_total_result = await db.execute(select(func.sum(AIUsage.costo_usd)))
    costo_total = round(costo_total_result.scalar() or 0.0, 6)

    # Score SEO promedio (desde SEOAuditLog)
    from models.seo_strategy import SEOAuditLog
    avg_score_result = await db.execute(
        select(func.avg(SEOAuditLog.puntuacion))
    )
    avg_score = round(avg_score_result.scalar() or 0.0, 1)

    # Posts pendientes de revisión
    posts_revision_result = await db.execute(
        select(BlogPost).where(BlogPost.estado == "en_revision")
        .order_by(desc(BlogPost.created_at)).limit(10)
    )
    posts_revision = posts_revision_result.scalars().all()

    # Clientes con más posts
    clients_result = await db.execute(
        select(Client).order_by(desc(Client.id)).limit(10)
    )
    clients = clients_result.scalars().all()

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "total_clients": total_clients,
        "total_posts": total_posts,
        "published_posts": published_posts,
        "pending_posts": pending_posts,
        "costo_total": costo_total,
        "avg_score": avg_score,
        "posts_revision": posts_revision,
        "clients": clients,
        "active_page": "dashboard",
    })


@router.get("/clients/", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
async def clients_list(request: Request, q: str = "", db: AsyncSession = Depends(get_db)):
    """Lista de clientes."""
    query = select(Client).order_by(desc(Client.id))
    if q:
        query = query.where(Client.nombre.ilike(f"%{q}%"))
    result = await db.execute(query)
    clients = result.scalars().all()

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("admin/partials/clients_table.html", {
            "request": request,
            "clients": clients,
        })

    return templates.TemplateResponse("admin/clients.html", {
        "request": request,
        "clients": clients,
        "q": q,
        "active_page": "clients",
    })


@router.get("/clients/new", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
async def client_new(request: Request):
    """Formulario para crear un nuevo cliente."""
    return templates.TemplateResponse("admin/client_form.html", {
        "request": request,
        "active_page": "clients",
    })


@router.post("/clients/create", dependencies=[Depends(require_auth)])
async def client_create(request: Request, db: AsyncSession = Depends(get_db)):
    """Procesa la creación de un nuevo cliente desde el formulario."""
    form = await request.form()

    nombre = form.get("nombre", "").strip()
    email = form.get("email", "").strip()
    industria = form.get("industria", "").strip()
    sitio_web = form.get("sitio_web", "").strip()
    blog_domain = form.get("blog_domain", "").strip()
    tono_de_marca = form.get("tono_de_marca", "profesional")
    idioma = form.get("idioma", "es")
    audiencia_objetivo = form.get("audiencia_objetivo", "").strip()
    descripcion_negocio = form.get("descripcion_negocio", "").strip()
    palabras_clave_nicho = form.get("palabras_clave_nicho", "")
    plan = form.get("plan", "free")
    frecuencia_publicacion = form.get("frecuencia_publicacion", "semanal")

    # Auto-generar slug del nombre si viene vacío
    blog_slug = form.get("blog_slug", "").strip()
    if not blog_slug:
        blog_slug = nombre.lower().strip()
        blog_slug = re.sub(r'[áàäâ]', 'a', blog_slug)
        blog_slug = re.sub(r'[éèëê]', 'e', blog_slug)
        blog_slug = re.sub(r'[íìïî]', 'i', blog_slug)
        blog_slug = re.sub(r'[óòöô]', 'o', blog_slug)
        blog_slug = re.sub(r'[úùüû]', 'u', blog_slug)
        blog_slug = re.sub(r'[ñ]', 'n', blog_slug)
        blog_slug = re.sub(r'[^a-z0-9\s-]', '', blog_slug)
        blog_slug = re.sub(r'[\s]+', '-', blog_slug)
        blog_slug = re.sub(r'-+', '-', blog_slug).strip('-')

    # Convertir palabras_clave_nicho de string CSV a lista
    kw_list = [k.strip() for k in palabras_clave_nicho.split(",") if k.strip()]

    client = Client(
        nombre=nombre,
        email=email or f"sin-email-{blog_slug}@blogengine.local",
        industria=industria,
        sitio_web=sitio_web,
        blog_slug=blog_slug,
        blog_domain=blog_domain or None,
        tono_de_marca=tono_de_marca,
        idioma=idioma,
        audiencia_objetivo=audiencia_objetivo,
        descripcion_negocio=descripcion_negocio,
        palabras_clave_nicho=kw_list if kw_list else None,
        plan=plan,
        frecuencia_publicacion=frecuencia_publicacion,
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)
    logger.info(f"[Dashboard] Cliente creado: {client.nombre} (id={client.id}) slug={blog_slug}")

    # Auto-disparar keyword research para el nuevo cliente (si Redis/Celery está activo)
    try:
        task_research_keywords.delay(client.id)
        logger.info(f"[Dashboard] task_research_keywords encolada para cliente {client.id}")
    except Exception as celery_err:
        logger.warning(f"[Dashboard] Celery no disponible, research no encolado: {celery_err}")

    return RedirectResponse(f"/admin/clients/{client.id}/", status_code=303)


@router.get("/clients/{client_id}/", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
async def client_detail(request: Request, client_id: int, db: AsyncSession = Depends(get_db)):
    """Detalle de cliente con tabs."""
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    posts_result = await db.execute(
        select(BlogPost).where(BlogPost.client_id == client_id)
        .order_by(desc(BlogPost.created_at)).limit(20)
    )
    posts = posts_result.scalars().all()

    keywords_result = await db.execute(
        select(SEOKeyword).where(SEOKeyword.client_id == client_id)
        .order_by(SEOKeyword.prioridad.desc()).limit(30)
    )
    keywords = keywords_result.scalars().all()

    money_pages_result = await db.execute(
        select(MoneyPage).where(MoneyPage.client_id == client_id)
        .order_by(MoneyPage.prioridad.desc())
    )
    money_pages = money_pages_result.scalars().all()

    clusters_result = await db.execute(
        select(TopicCluster).where(TopicCluster.client_id == client_id)
    )
    clusters = clusters_result.scalars().all()

    return templates.TemplateResponse("admin/client_detail.html", {
        "request": request,
        "client": client,
        "posts": posts,
        "keywords": keywords,
        "money_pages": money_pages,
        "clusters": clusters,
        "active_page": "clients",
    })


@router.delete("/clients/{client_id}/delete", dependencies=[Depends(require_auth)])
async def client_delete(client_id: int, db: AsyncSession = Depends(get_db)):
    """Elimina un cliente y todos sus datos relacionados."""
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Borrar en orden para respetar FKs sin CASCADE configurado
    await db.execute(delete(SEOAuditLog).where(SEOAuditLog.client_id == client_id))
    await db.execute(delete(SocialPost).where(SocialPost.client_id == client_id))
    await db.execute(delete(CalendarEntry).where(CalendarEntry.client_id == client_id))
    await db.execute(delete(AIUsage).where(AIUsage.client_id == client_id))
    await db.execute(delete(SEOKeyword).where(SEOKeyword.client_id == client_id))
    await db.execute(delete(TopicCluster).where(TopicCluster.client_id == client_id))
    await db.execute(delete(MoneyPage).where(MoneyPage.client_id == client_id))
    await db.execute(delete(BlogPost).where(BlogPost.client_id == client_id))
    await db.delete(client)
    await db.commit()

    logger.info(f"[Dashboard] Cliente eliminado: {client.nombre} (id={client_id})")
    # Devolver string vacío → HTMX remueve la fila con outerHTML swap
    return HTMLResponse(content="")


@router.get("/posts/", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
async def posts_list(request: Request, estado: str = "", client_id: int = 0, db: AsyncSession = Depends(get_db)):
    """Lista de posts con filtros."""
    query = select(BlogPost).order_by(desc(BlogPost.created_at)).limit(50)
    if estado:
        query = select(BlogPost).where(BlogPost.estado == estado).order_by(desc(BlogPost.created_at)).limit(50)
    if client_id:
        base = select(BlogPost).where(BlogPost.client_id == client_id)
        if estado:
            base = select(BlogPost).where(BlogPost.client_id == client_id, BlogPost.estado == estado)
        query = base.order_by(desc(BlogPost.created_at)).limit(50)

    result = await db.execute(query)
    posts = result.scalars().all()

    clients_result = await db.execute(select(Client).order_by(Client.nombre))
    clients = clients_result.scalars().all()

    return templates.TemplateResponse("admin/posts.html", {
        "request": request,
        "posts": posts,
        "clients": clients,
        "estado_filter": estado,
        "client_filter": client_id,
        "active_page": "posts",
    })


@router.get("/posts/{post_id}/", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
async def post_detail(request: Request, post_id: int, db: AsyncSession = Depends(get_db)):
    """Detalle del post con audit SEO."""
    post = await db.get(BlogPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post no encontrado")

    client = await db.get(Client, post.client_id)

    return templates.TemplateResponse("admin/post_detail.html", {
        "request": request,
        "post": post,
        "client": client,
        "active_page": "posts",
    })


@router.post("/posts/{post_id}/approve", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
async def approve_post(request: Request, post_id: int, db: AsyncSession = Depends(get_db)):
    """Aprueba un post (HTMX action)."""
    post = await db.get(BlogPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post no encontrado")
    post.estado = "aprobado"
    await db.commit()
    await db.refresh(post)
    return templates.TemplateResponse("admin/partials/post_estado_badge.html", {
        "request": request,
        "post": post,
    })


@router.post("/posts/{post_id}/publish", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
async def publish_post_admin(request: Request, post_id: int, db: AsyncSession = Depends(get_db)):
    """Publica un post (HTMX action)."""
    from datetime import datetime, timezone
    post = await db.get(BlogPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post no encontrado")
    post.estado = "publicado"
    post.fecha_publicado = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(post)
    return templates.TemplateResponse("admin/partials/post_estado_badge.html", {
        "request": request,
        "post": post,
    })
