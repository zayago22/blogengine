"""
BlogEngine - API de Publicación.
Como BlogEngine sirve los blogs directamente, "publicar" significa cambiar
el estado del post a "publicado" y hacerlo visible en el blog del cliente.

Opcionalmente distribuye a redes sociales.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.base import get_db
from models.client import Client
from models.blog_post import BlogPost
from core.content_engine import ContentEngine

router = APIRouter()


@router.post("/{post_id}/go-live")
async def publicar_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """
    Publica un artículo: lo hace visible en el blog del cliente.
    
    BlogEngine sirve el blog directamente, así que publicar = cambiar estado.
    El artículo estará disponible inmediatamente en:
      - blogengine.app/b/{blog_slug}/{post_slug}
      - {dominio_personalizado}/{post_slug} (si configurado)
    """
    result = await db.execute(select(BlogPost).where(BlogPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post no encontrado")
    if post.estado not in ("aprobado", "en_revision", "borrador"):
        raise HTTPException(
            status_code=400, 
            detail=f"No se puede publicar post en estado '{post.estado}'"
        )

    # Obtener cliente para construir la URL
    result = await db.execute(select(Client).where(Client.id == post.client_id))
    client = result.scalar_one_or_none()

    # Publicar
    post.estado = "publicado"
    post.fecha_publicado = datetime.utcnow()
    
    # Construir URL del post
    if client.blog_domain:
        post.url_publicado = f"https://{client.blog_domain}/{post.slug}"
    elif client.blog_slug:
        post.url_publicado = f"https://blogengine.app/b/{client.blog_slug}/{post.slug}"
    
    await db.flush()
    
    return {
        "status": "ok",
        "mensaje": f"Artículo publicado: {post.titulo}",
        "url": post.url_publicado,
    }


@router.post("/{post_id}/unpublish")
async def despublicar_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Despublica un artículo (lo oculta del blog público)."""
    result = await db.execute(select(BlogPost).where(BlogPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post no encontrado")
    
    post.estado = "borrador"
    post.fecha_publicado = None
    await db.flush()
    return {"status": "ok", "mensaje": "Artículo despublicado"}


@router.post("/{post_id}/distribute")
async def distribuir_a_redes(post_id: int, db: AsyncSession = Depends(get_db)):
    """
    Distribuye un artículo publicado a las redes sociales del cliente.
    Genera copies adaptados con DeepSeek y los publica en cada red configurada.
    """
    result = await db.execute(select(BlogPost).where(BlogPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post no encontrado")
    if post.estado != "publicado":
        raise HTTPException(status_code=400, detail="El post debe estar publicado primero")

    result = await db.execute(select(Client).where(Client.id == post.client_id))
    client = result.scalar_one_or_none()

    redes_disponibles = client.redes_activas
    if not redes_disponibles:
        return {"status": "warning", "mensaje": "No hay redes sociales configuradas"}

    # Generar copies para cada red
    engine = ContentEngine(db)
    from core.content_engine import ArticuloGenerado
    articulo = ArticuloGenerado(
        titulo=post.titulo,
        slug=post.slug,
        meta_description=post.meta_description or "",
        contenido_html=post.contenido_html or "",
        extracto=post.extracto or "",
        keyword_principal=post.keyword_principal or "",
        keywords_secundarias=post.keywords_secundarias or [],
        costo_total_usd=0, tokens_total=0,
        proveedor_generacion="", modelo_generacion="",
    )

    copies = await engine.generar_copies_sociales(client, articulo, redes_disponibles)

    # TODO: Publicar en cada red con los distribuidores
    post.distribuido_a = redes_disponibles
    await db.flush()

    return {
        "status": "ok",
        "copies": {red: c[:200] + "..." if len(c) > 200 else c for red, c in copies.items()},
        "redes": redes_disponibles,
    }


@router.post("/{post_id}/full-pipeline")
async def pipeline_completo(post_id: int, db: AsyncSession = Depends(get_db)):
    """Pipeline completo: publica el artículo + distribuye a redes sociales."""
    # Publicar
    pub_result = await publicar_post(post_id, db)
    # Distribuir
    dist_result = await distribuir_a_redes(post_id, db)

    return {
        "status": "ok",
        "publicacion": pub_result,
        "distribucion": dist_result,
    }
