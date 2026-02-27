"""
BlogEngine - API SEO-First.
Toda la operación gira alrededor del SEO del cliente.

FLUJO DE TRABAJO:
=================
1. Crear cliente
2. Registrar sus money pages (páginas donde convierte)
3. Investigar keywords con IA → genera clusters y calendario
4. Generar artículos desde keywords de la estrategia
5. Cada artículo pasa auditoría SEO antes de publicar
6. Post-publicación: trackear posiciones en Google
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models.base import get_db
from models.client import Client
from models.blog_post import BlogPost
from models.seo_strategy import MoneyPage, TopicCluster, SEOKeyword, SEOAuditLog
from core.content_engine import ContentEngine
from core.seo_engine import SetupGuideGenerator, GoogleIndexingService

router = APIRouter()


# =============================================================================
# SCHEMAS
# =============================================================================

class MoneyPageCreate(BaseModel):
    """Registrar una página de dinero del cliente."""
    url: str = Field(..., description="URL de la página: https://cliente.com/servicios/renta")
    titulo: str = Field(..., description="Nombre descriptivo: 'Servicio de renta'")
    tipo: str = Field(default="servicio", description="servicio | producto | contacto | landing | whatsapp")
    keywords_target: list[str] = Field(default=[], description="Keywords que esta página debería rankear")
    anchor_texts: list[str] = Field(default=[], description="Textos ancla variados para links desde el blog")
    prioridad: int = Field(default=3, ge=1, le=5, description="1=baja, 5=máxima")


class MoneyPageResponse(BaseModel):
    id: int
    url: str
    titulo: str
    tipo: str
    keywords_target: list = []
    anchor_texts: list = []
    prioridad: int
    activa: bool
    model_config = {"from_attributes": True}


class KeywordResponse(BaseModel):
    id: int
    keyword: str
    keywords_secundarias: list = []
    intencion: str
    dificultad_estimada: str
    volumen_estimado: str
    titulo_sugerido: Optional[str] = None
    prioridad: int
    es_pillar: bool
    estado: str
    cluster_nombre: Optional[str] = None
    seo_score: Optional[int] = None
    posicion_actual: Optional[int] = None


class GenerateFromKeywordRequest(BaseModel):
    keyword_id: int = Field(..., description="ID de la keyword de la estrategia")


class GenerateDirectRequest(BaseModel):
    keyword: str = Field(..., min_length=2, description="Keyword principal a atacar")
    keywords_secundarias: list[str] = Field(default=[], description="3-5 keywords secundarias")
    titulo_sugerido: str = Field(default="", description="Título sugerido (opcional)")


class SEOConfigUpdate(BaseModel):
    integration_level: str = Field(..., description="subdirectory | subdomain | external")
    canonical_domain: Optional[str] = None
    blog_base_url: Optional[str] = None
    proxy_path: str = Field(default="/blog")
    google_analytics_id: Optional[str] = None
    default_author: Optional[str] = None
    social_profiles: list[str] = Field(default=[])


# =============================================================================
# MONEY PAGES — Dónde convierte el cliente
# =============================================================================

@router.post("/{client_id}/money-pages", response_model=MoneyPageResponse, status_code=201)
async def crear_money_page(
    client_id: int, data: MoneyPageCreate, db: AsyncSession = Depends(get_db)
):
    """
    Registra una página de dinero del cliente.
    
    Estas son las URLs más importantes del negocio: donde vende,
    donde genera leads, donde tiene su formulario de contacto.
    CADA artículo del blog enlazará a estas páginas.
    
    Ejemplo para Raíz Rentable:
    - https://raizrentable.com/propiedades → "Ver propiedades disponibles"
    - https://raizrentable.com/contacto → "Agenda una cita con un asesor"
    - https://wa.me/5215512345678 → "Contáctanos por WhatsApp"
    """
    result = await db.execute(select(Client).where(Client.id == client_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    mp = MoneyPage(
        client_id=client_id,
        url=data.url,
        titulo=data.titulo,
        tipo=data.tipo,
        keywords_target=data.keywords_target,
        anchor_texts=data.anchor_texts if data.anchor_texts else [data.titulo],
        prioridad=data.prioridad,
    )
    db.add(mp)
    await db.commit()
    await db.refresh(mp)
    return mp


@router.get("/{client_id}/money-pages", response_model=list[MoneyPageResponse])
async def listar_money_pages(client_id: int, db: AsyncSession = Depends(get_db)):
    """Lista todas las money pages de un cliente."""
    result = await db.execute(
        select(MoneyPage)
        .where(MoneyPage.client_id == client_id)
        .order_by(MoneyPage.prioridad.desc())
    )
    return list(result.scalars().all())


@router.delete("/{client_id}/money-pages/{mp_id}", status_code=204)
async def eliminar_money_page(client_id: int, mp_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MoneyPage).where(MoneyPage.id == mp_id, MoneyPage.client_id == client_id)
    )
    mp = result.scalar_one_or_none()
    if not mp:
        raise HTTPException(status_code=404, detail="Money page no encontrada")
    await db.delete(mp)
    await db.commit()


# =============================================================================
# KEYWORD RESEARCH — IA investiga qué keywords atacar
# =============================================================================

@router.post("/{client_id}/research")
async def investigar_keywords(
    client_id: int,
    num_keywords: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """
    Genera estrategia de keywords con IA.
    
    La IA analiza:
    - Industria del cliente
    - Sus servicios/productos (money pages)
    - Keywords ya atacadas (para no repetir)
    
    Produce:
    - Clusters temáticos organizados por silo
    - Keywords priorizadas por dificultad/volumen
    - Calendario editorial sugerido
    
    IMPORTANTE: Registrar money pages ANTES de investigar.
    """
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Verificar que tenga money pages
    mp_count = await db.execute(
        select(func.count(MoneyPage.id)).where(
            MoneyPage.client_id == client_id, MoneyPage.activa == True
        )
    )
    if mp_count.scalar() == 0:
        raise HTTPException(
            status_code=400,
            detail="Registra al menos 1 money page antes de investigar keywords. "
                   "POST /api/seo/{client_id}/money-pages",
        )

    engine = ContentEngine(db)
    strategy = await engine.research_keywords(client, num_keywords)

    return {
        "status": "ok",
        "clusters": len(strategy.get("clusters", [])),
        "keywords_generadas": sum(
            len(c.get("keywords", [])) + 1  # +1 por pillar
            for c in strategy.get("clusters", [])
        ),
        "estrategia": strategy,
    }


@router.get("/{client_id}/keywords")
async def listar_keywords(
    client_id: int,
    estado: Optional[str] = None,
    cluster_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Lista keywords de la estrategia del cliente.
    Filtrable por estado (pendiente, publicado, descartado) y cluster.
    """
    query = select(SEOKeyword).where(SEOKeyword.client_id == client_id)
    if estado:
        query = query.where(SEOKeyword.estado == estado)
    if cluster_id:
        query = query.where(SEOKeyword.cluster_id == cluster_id)

    result = await db.execute(query.order_by(SEOKeyword.prioridad.desc()))
    keywords = result.scalars().all()

    # Obtener nombres de clusters
    cluster_ids = {kw.cluster_id for kw in keywords if kw.cluster_id}
    cluster_names = {}
    if cluster_ids:
        clusters = await db.execute(
            select(TopicCluster).where(TopicCluster.id.in_(cluster_ids))
        )
        cluster_names = {c.id: c.nombre for c in clusters.scalars().all()}

    # Obtener scores SEO de posts generados
    post_ids = {kw.blog_post_id for kw in keywords if kw.blog_post_id}
    audit_scores = {}
    if post_ids:
        audits = await db.execute(
            select(SEOAuditLog).where(SEOAuditLog.blog_post_id.in_(post_ids))
        )
        audit_scores = {a.blog_post_id: a.puntuacion for a in audits.scalars().all()}

    return [
        KeywordResponse(
            id=kw.id,
            keyword=kw.keyword,
            keywords_secundarias=kw.keywords_secundarias or [],
            intencion=kw.intencion,
            dificultad_estimada=kw.dificultad_estimada,
            volumen_estimado=kw.volumen_estimado,
            titulo_sugerido=kw.titulo_sugerido,
            prioridad=kw.prioridad,
            es_pillar=kw.es_pillar,
            estado=kw.estado,
            cluster_nombre=cluster_names.get(kw.cluster_id),
            seo_score=audit_scores.get(kw.blog_post_id),
            posicion_actual=kw.posicion_actual,
        )
        for kw in keywords
    ]


@router.get("/{client_id}/clusters")
async def listar_clusters(client_id: int, db: AsyncSession = Depends(get_db)):
    """Lista clusters temáticos con progreso."""
    result = await db.execute(
        select(TopicCluster).where(TopicCluster.client_id == client_id)
    )
    clusters = result.scalars().all()

    response = []
    for cluster in clusters:
        # Contar keywords del cluster
        kw_result = await db.execute(
            select(
                func.count(SEOKeyword.id).label("total"),
                func.count(SEOKeyword.blog_post_id).label("generados"),
            ).where(SEOKeyword.cluster_id == cluster.id)
        )
        stats = kw_result.one()

        response.append({
            "id": cluster.id,
            "nombre": cluster.nombre,
            "pillar_keyword": cluster.pillar_keyword,
            "pillar_titulo_sugerido": cluster.pillar_titulo_sugerido,
            "estado": cluster.estado,
            "keywords_total": stats.total,
            "keywords_generados": stats.generados,
            "progreso": f"{stats.generados}/{stats.total}",
        })

    return response


# =============================================================================
# GENERACIÓN DESDE ESTRATEGIA SEO
# =============================================================================

@router.post("/{client_id}/generate/from-keyword")
async def generar_desde_keyword(
    client_id: int,
    data: GenerateFromKeywordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Genera artículo para una keyword de la estrategia.
    
    El artículo se genera con:
    - Prompt SEO-first (keyword density, H2s, primer párrafo)
    - Money links del cliente inyectados
    - Internal links a artículos existentes
    - Auditoría SEO automática
    - Corrección automática si no pasa la auditoría
    """
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    engine = ContentEngine(db)
    gen_result = await engine.generate_for_keyword(client, data.keyword_id)

    return {
        "status": "ok",
        "blog_post_id": gen_result.blog_post_id,
        "titulo": gen_result.titulo,
        "keyword": gen_result.keyword_principal,
        "seo_score": gen_result.seo_score,
        "seo_passed": gen_result.seo_passed,
        "revision_count": gen_result.revision_count,
        "costo_usd": gen_result.costo_total_usd,
        "problemas_seo": gen_result.problemas_seo,
        "mensaje": (
            f"✅ Artículo aprobado (SEO: {gen_result.seo_score}/100)"
            if gen_result.seo_passed
            else f"⚠️ Requiere revisión manual (SEO: {gen_result.seo_score}/100)"
        ),
    }


@router.post("/{client_id}/generate/direct")
async def generar_directo(
    client_id: int,
    data: GenerateDirectRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Genera artículo con keyword directa (sin pasar por la estrategia).
    Útil para artículos de oportunidad o temas específicos.
    """
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    engine = ContentEngine(db)
    gen_result = await engine.generate_article(
        client=client,
        keyword=data.keyword,
        keywords_secundarias=data.keywords_secundarias,
        titulo_sugerido=data.titulo_sugerido,
    )

    return {
        "status": "ok",
        "blog_post_id": gen_result.blog_post_id,
        "titulo": gen_result.titulo,
        "keyword": gen_result.keyword_principal,
        "seo_score": gen_result.seo_score,
        "seo_passed": gen_result.seo_passed,
        "costo_usd": gen_result.costo_total_usd,
        "problemas_seo": gen_result.problemas_seo,
    }


@router.post("/{client_id}/generate/batch")
async def generar_batch(
    client_id: int,
    cantidad: int = 4,
    db: AsyncSession = Depends(get_db),
):
    """
    Genera múltiples artículos de la estrategia en batch.
    Toma las keywords pendientes de mayor prioridad.
    """
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Obtener keywords pendientes
    result = await db.execute(
        select(SEOKeyword)
        .where(
            SEOKeyword.client_id == client_id,
            SEOKeyword.estado == "pendiente",
        )
        .order_by(SEOKeyword.prioridad.desc(), SEOKeyword.es_pillar.desc())
        .limit(cantidad)
    )
    keywords = result.scalars().all()

    if not keywords:
        raise HTTPException(
            status_code=400,
            detail="No hay keywords pendientes. Ejecuta /research primero.",
        )

    engine = ContentEngine(db)
    resultados = []

    for kw in keywords:
        try:
            gen_result = await engine.generate_for_keyword(client, kw.id)
            resultados.append({
                "keyword": kw.keyword,
                "blog_post_id": gen_result.blog_post_id,
                "seo_score": gen_result.seo_score,
                "seo_passed": gen_result.seo_passed,
                "costo_usd": gen_result.costo_total_usd,
                "status": "ok",
            })
        except Exception as e:
            resultados.append({
                "keyword": kw.keyword,
                "status": "error",
                "error": str(e),
            })

    exitosos = sum(1 for r in resultados if r["status"] == "ok")
    costo_total = sum(r.get("costo_usd", 0) for r in resultados)

    return {
        "status": "ok",
        "generados": exitosos,
        "total": len(keywords),
        "costo_total_usd": round(costo_total, 4),
        "resultados": resultados,
    }


# =============================================================================
# AUDITORÍAS SEO
# =============================================================================

@router.get("/{client_id}/audits")
async def listar_auditorias(
    client_id: int,
    aprobado: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    """Lista auditorías SEO de los artículos del cliente."""
    query = select(SEOAuditLog).where(SEOAuditLog.client_id == client_id)
    if aprobado is not None:
        query = query.where(SEOAuditLog.aprobado == aprobado)

    result = await db.execute(query.order_by(SEOAuditLog.created_at.desc()))
    audits = result.scalars().all()

    return [
        {
            "id": a.id,
            "blog_post_id": a.blog_post_id,
            "keyword": a.keyword_principal,
            "puntuacion": a.puntuacion,
            "aprobado": a.aprobado,
            "revision_automatica": a.revision_automatica,
            "problemas": a.problemas_criticos,
            "stats": a.stats,
        }
        for a in audits
    ]


@router.post("/{client_id}/audit/{post_id}")
async def auditar_post(client_id: int, post_id: int, db: AsyncSession = Depends(get_db)):
    """Ejecuta auditoría SEO manualmente en un post existente."""
    result = await db.execute(
        select(BlogPost).where(BlogPost.id == post_id, BlogPost.client_id == client_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post no encontrado")

    from core.seo_strategy import OnPageSEOOptimizer
    audit = OnPageSEOOptimizer.audit(
        titulo=post.titulo,
        meta_description=post.meta_description or "",
        slug=post.slug,
        contenido_html=post.contenido_html or "",
        keyword_principal=post.keyword_principal or "",
        keywords_secundarias=post.keywords_secundarias or [],
    )

    return audit


# =============================================================================
# CONFIGURACIÓN SEO TÉCNICA
# =============================================================================

@router.patch("/{client_id}/config")
async def configurar_seo(
    client_id: int, data: SEOConfigUpdate, db: AsyncSession = Depends(get_db)
):
    """Configura parámetros SEO técnicos (canonical, integración, analytics)."""
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    client.seo_integration_level = data.integration_level
    client.seo_canonical_domain = data.canonical_domain
    client.seo_blog_base_url = data.blog_base_url
    client.seo_proxy_path = data.proxy_path
    client.seo_google_analytics_id = data.google_analytics_id
    client.seo_default_author = data.default_author
    client.seo_social_profiles = data.social_profiles

    if data.integration_level == "subdomain" and data.canonical_domain:
        client.blog_domain = data.canonical_domain

    await db.flush()
    return {"status": "ok", "nivel": data.integration_level}


@router.get("/{client_id}/setup-guide")
async def guia_setup(client_id: int, db: AsyncSession = Depends(get_db)):
    """Genera instrucciones de configuración de DNS/proxy para el cliente."""
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    domain = (client.seo_canonical_domain or client.sitio_web).replace("https://", "").replace("http://", "").split("/")[0]
    return SetupGuideGenerator.generate_guide(
        integration_level=client.seo_integration_level or "subdomain",
        client_domain=domain,
        blog_slug=client.blog_slug or client.nombre.lower().replace(" ", "-"),
    )


@router.get("/{client_id}/diagnostic")
async def diagnostico_seo(client_id: int, db: AsyncSession = Depends(get_db)):
    """Diagnóstico SEO completo: técnico + contenido + estrategia."""
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Stats
    mp_count = (await db.execute(
        select(func.count(MoneyPage.id)).where(MoneyPage.client_id == client_id, MoneyPage.activa == True)
    )).scalar()

    kw_total = (await db.execute(
        select(func.count(SEOKeyword.id)).where(SEOKeyword.client_id == client_id)
    )).scalar()

    kw_published = (await db.execute(
        select(func.count(SEOKeyword.id)).where(
            SEOKeyword.client_id == client_id, SEOKeyword.estado == "publicado"
        )
    )).scalar()

    posts_published = (await db.execute(
        select(func.count(BlogPost.id)).where(
            BlogPost.client_id == client_id, BlogPost.estado == "publicado"
        )
    )).scalar()

    avg_seo = (await db.execute(
        select(func.avg(SEOAuditLog.puntuacion)).where(SEOAuditLog.client_id == client_id)
    )).scalar()

    problemas = []
    recomendaciones = []
    puntuacion = 0

    # Money pages
    if mp_count == 0:
        problemas.append("❌ Sin money pages. El blog no sabe a dónde enviar tráfico.")
    elif mp_count < 2:
        recomendaciones.append("💡 Agrega más money pages para diversificar los links.")
        puntuacion += 10
    else:
        puntuacion += 20

    # Estrategia de keywords
    if kw_total == 0:
        problemas.append("❌ Sin estrategia de keywords. Ejecuta /research para crearla.")
    else:
        puntuacion += 15
        if kw_published < kw_total * 0.25:
            recomendaciones.append(f"💡 Solo {kw_published}/{kw_total} keywords tienen artículo. Genera más contenido.")
        else:
            puntuacion += 10

    # Posts publicados
    if posts_published == 0:
        problemas.append("❌ Sin artículos publicados.")
    elif posts_published < 5:
        recomendaciones.append(f"💡 Solo {posts_published} artículos publicados. Google necesita volumen.")
        puntuacion += 10
    else:
        puntuacion += 20

    # SEO score promedio
    if avg_seo:
        puntuacion += min(int(avg_seo * 0.2), 20)
        if avg_seo < 70:
            recomendaciones.append(f"⚠️ Score SEO promedio: {avg_seo:.0f}/100. Revisar y corregir artículos.")

    # Config técnica
    if client.seo_canonical_domain:
        puntuacion += 5
    else:
        problemas.append("❌ Falta canonical domain.")
    if client.seo_google_analytics_id:
        puntuacion += 5
    else:
        recomendaciones.append("💡 Agrega Google Analytics para medir tráfico.")
    if client.blog_slug:
        puntuacion += 5
    else:
        problemas.append("❌ Falta blog_slug.")

    return {
        "puntuacion": min(puntuacion, 100),
        "stats": {
            "money_pages": mp_count,
            "keywords_total": kw_total,
            "keywords_publicadas": kw_published,
            "posts_publicados": posts_published,
            "seo_score_promedio": round(avg_seo, 1) if avg_seo else None,
        },
        "problemas": problemas,
        "recomendaciones": recomendaciones,
    }


@router.post("/{client_id}/ping-google")
async def notificar_google(client_id: int, db: AsyncSession = Depends(get_db)):
    """Notifica a Google y Bing que hay contenido nuevo."""
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404)

    blog_url = client.seo_blog_base_url or f"https://blogengine.app/b/{client.blog_slug}"
    sitemap = f"{blog_url}/sitemap.xml"

    google_ok = await GoogleIndexingService.ping_sitemap(sitemap)
    bing_ok = await GoogleIndexingService.ping_bing_sitemap(sitemap)

    return {"google": "✅" if google_ok else "❌", "bing": "✅" if bing_ok else "❌", "sitemap": sitemap}
