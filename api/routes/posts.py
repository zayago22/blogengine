"""
BlogEngine - API de Blog Posts.
Generación, listado y gestión de artículos de blog.
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.base import get_db
from models.client import Client
from models.blog_post import BlogPost
from core.content_engine import ContentEngine

router = APIRouter()


# --- Schemas ---

class PostGenerate(BaseModel):
    """Schema para generar un artículo (keyword-first)."""
    client_id: int
    keyword: str = Field(..., min_length=2, max_length=200, description="Keyword principal a posicionar")
    keywords_secundarias: list[str] = Field(default=[], description="3-5 keywords secundarias")
    fecha_programada: Optional[datetime] = None


class PostResponse(BaseModel):
    """Schema de respuesta de un blog post."""
    id: int
    client_id: int
    titulo: str
    slug: str
    estado: str
    keyword_principal: Optional[str] = None
    fecha_programada: Optional[datetime] = None
    fecha_publicado: Optional[datetime] = None
    url_publicado: Optional[str] = None
    proveedor_generacion: Optional[str] = None
    costo_ia_total_usd: float = 0.0

    model_config = {"from_attributes": True}


class PostDetail(PostResponse):
    """Schema detallado de un blog post (incluye contenido)."""
    meta_description: Optional[str] = None
    contenido_html: Optional[str] = None
    extracto: Optional[str] = None
    keywords_secundarias: Optional[list] = []
    proveedor_revision: Optional[str] = None
    modelo_generacion: Optional[str] = None
    modelo_revision: Optional[str] = None
    tokens_input_total: int = 0
    tokens_output_total: int = 0
    distribuido_a: Optional[list] = []

    model_config = {"from_attributes": True}


# --- Endpoints ---

@router.get("/", response_model=list[PostResponse])
async def listar_posts(
    client_id: Optional[int] = None,
    estado: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Lista blog posts, opcionalmente filtrados por cliente o estado."""
    query = select(BlogPost)
    if client_id:
        query = query.where(BlogPost.client_id == client_id)
    if estado:
        query = query.where(BlogPost.estado == estado)
    
    result = await db.execute(query.order_by(BlogPost.created_at.desc()))
    posts = result.scalars().all()
    return posts


@router.get("/{post_id}", response_model=PostDetail)
async def obtener_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Obtiene un blog post con todo su contenido."""
    result = await db.execute(select(BlogPost).where(BlogPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post no encontrado")
    return post


@router.post("/generate", response_model=PostDetail, status_code=201)
async def generar_post(data: PostGenerate, db: AsyncSession = Depends(get_db)):
    """
    Genera un nuevo artículo de blog con pipeline SEO-first.
    
    ⚠️ RECOMENDACIÓN: Para mejor SEO, usa el flujo de /api/seo/:
    1. POST /api/seo/{client_id}/money-pages → registrar páginas de dinero
    2. POST /api/seo/{client_id}/research → investigar keywords
    3. POST /api/seo/{client_id}/generate/from-keyword → generar desde estrategia
    
    Este endpoint permite generar con keyword directa.
    """
    # Verificar que el cliente existe
    result = await db.execute(select(Client).where(Client.id == data.client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    if client.estado != "activo":
        raise HTTPException(status_code=400, detail="Cliente no está activo")

    # Generar artículo con pipeline SEO-first
    engine = ContentEngine(db)
    try:
        gen_result = await engine.generate_article(
            client=client,
            keyword=data.keyword,
            keywords_secundarias=data.keywords_secundarias,
        )

        # Obtener el post generado
        result = await db.execute(
            select(BlogPost).where(BlogPost.id == gen_result.blog_post_id)
        )
        blog_post = result.scalar_one_or_none()
        
        if data.fecha_programada:
            blog_post.fecha_programada = data.fecha_programada
            await db.flush()
            await db.refresh(blog_post)

        return blog_post

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/{post_id}/approve")
async def aprobar_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Aprueba un post para publicación."""
    result = await db.execute(select(BlogPost).where(BlogPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post no encontrado")
    if post.estado not in ("en_revision", "borrador"):
        raise HTTPException(status_code=400, detail=f"No se puede aprobar post en estado '{post.estado}'")
    
    post.estado = "aprobado"
    await db.flush()
    return {"status": "ok", "mensaje": "Post aprobado y listo para publicar"}


@router.post("/{post_id}/reject")
async def rechazar_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Rechaza un post."""
    result = await db.execute(select(BlogPost).where(BlogPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post no encontrado")
    
    post.estado = "rechazado"
    await db.flush()
    return {"status": "ok", "mensaje": "Post rechazado"}


@router.delete("/{post_id}")
async def eliminar_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Elimina un post."""
    result = await db.execute(select(BlogPost).where(BlogPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post no encontrado")
    
    await db.delete(post)
    await db.flush()
    return {"status": "ok", "mensaje": "Post eliminado"}
