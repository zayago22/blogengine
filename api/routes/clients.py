"""
BlogEngine - API de Clientes.
CRUD completo para gestión de clientes (tenants).
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.base import get_db
from models.client import Client
from utils.encryption import encriptar

router = APIRouter()


# --- Schemas ---

class ClientCreate(BaseModel):
    """Schema para crear un cliente."""
    nombre: str = Field(..., min_length=2, max_length=200)
    email: str = Field(..., max_length=200)
    industria: str = Field(..., max_length=100)
    sitio_web: str = Field(..., max_length=500)
    tono_de_marca: str = Field(default="profesional")
    palabras_clave_nicho: list[str] = Field(default=[])
    audiencia_objetivo: str = Field(default="")
    idioma: str = Field(default="es")
    descripcion_negocio: str = Field(default="")
    plan: str = Field(default="free")
    frecuencia_publicacion: str = Field(default="semanal")
    auto_publish: bool = Field(default=False)
    prompt_industria: str = Field(default="general")
    # Blog hospedado
    blog_slug: Optional[str] = Field(default=None, description="Slug único: mi-empresa → blogengine.app/b/mi-empresa")
    blog_domain: Optional[str] = Field(default=None, description="Dominio personalizado: blog.miempresa.com")
    blog_design: Optional[dict] = Field(default=None, description="Diseño: {primary, background, text, accent, font, logo_url}")


class ClientUpdate(BaseModel):
    """Schema para actualizar un cliente."""
    nombre: Optional[str] = None
    email: Optional[str] = None
    industria: Optional[str] = None
    tono_de_marca: Optional[str] = None
    palabras_clave_nicho: Optional[list[str]] = None
    audiencia_objetivo: Optional[str] = None
    plan: Optional[str] = None
    estado: Optional[str] = None
    frecuencia_publicacion: Optional[str] = None
    auto_publish: Optional[bool] = None
    prompt_industria: Optional[str] = None


class CMSCredentials(BaseModel):
    """Schema para configurar credenciales de CMS."""
    cms_type: str
    cms_url: str
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    api_token: Optional[str] = None


class SocialCredentials(BaseModel):
    """Schema para configurar credenciales de una red social."""
    plataforma: str  # facebook, instagram, linkedin, twitter, pinterest, google_business
    account_id: Optional[str] = None
    access_token: str


class ClientResponse(BaseModel):
    """Schema de respuesta de cliente."""
    id: int
    nombre: str
    email: str
    industria: str
    sitio_web: str
    plan: str
    estado: str
    blog_slug: Optional[str] = None
    blog_domain: Optional[str] = None
    blog_url: Optional[str] = None
    redes_activas: list[str] = []

    model_config = {"from_attributes": True}


# --- Endpoints ---

@router.get("/", response_model=list[ClientResponse])
async def listar_clientes(
    estado: Optional[str] = None,
    plan: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Lista todos los clientes, opcionalmente filtrados por estado o plan."""
    query = select(Client)
    if estado:
        query = query.where(Client.estado == estado)
    if plan:
        query = query.where(Client.plan == plan)
    
    result = await db.execute(query.order_by(Client.nombre))
    clients = result.scalars().all()
    
    return [
        ClientResponse(
            id=c.id,
            nombre=c.nombre,
            email=c.email,
            industria=c.industria,
            sitio_web=c.sitio_web,
            plan=c.plan,
            estado=c.estado,
            blog_slug=c.blog_slug,
            blog_domain=c.blog_domain,
            blog_url=f"https://{c.blog_domain}" if c.blog_domain else (f"https://blogengine.app/b/{c.blog_slug}" if c.blog_slug else None),
            redes_activas=c.redes_activas,
        )
        for c in clients
    ]


@router.get("/{client_id}", response_model=ClientResponse)
async def obtener_cliente(client_id: int, db: AsyncSession = Depends(get_db)):
    """Obtiene un cliente por ID."""
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    return ClientResponse(
        id=client.id,
        nombre=client.nombre,
        email=client.email,
        industria=client.industria,
        sitio_web=client.sitio_web,
        plan=client.plan,
        estado=client.estado,
        blog_slug=client.blog_slug,
        blog_domain=client.blog_domain,
        blog_url=f"https://{client.blog_domain}" if client.blog_domain else (f"https://blogengine.app/b/{client.blog_slug}" if client.blog_slug else None),
        redes_activas=client.redes_activas,
    )


@router.post("/", response_model=ClientResponse, status_code=201)
async def crear_cliente(data: ClientCreate, db: AsyncSession = Depends(get_db)):
    """Crea un nuevo cliente."""
    client = Client(
        nombre=data.nombre,
        email=data.email,
        industria=data.industria,
        sitio_web=data.sitio_web,
        tono_de_marca=data.tono_de_marca,
        palabras_clave_nicho=data.palabras_clave_nicho,
        audiencia_objetivo=data.audiencia_objetivo,
        idioma=data.idioma,
        descripcion_negocio=data.descripcion_negocio,
        plan=data.plan,
        frecuencia_publicacion=data.frecuencia_publicacion,
        auto_publish=data.auto_publish,
        prompt_industria=data.prompt_industria,
        blog_slug=data.blog_slug or data.nombre.lower().replace(" ", "-"),
        blog_domain=data.blog_domain,
        blog_design=data.blog_design or {},
    )
    db.add(client)
    await db.flush()
    await db.refresh(client)

    return ClientResponse(
        id=client.id,
        nombre=client.nombre,
        email=client.email,
        industria=client.industria,
        sitio_web=client.sitio_web,
        plan=client.plan,
        estado=client.estado,
        blog_slug=client.blog_slug,
        blog_domain=client.blog_domain,
        blog_url=f"https://{client.blog_domain}" if client.blog_domain else (f"https://blogengine.app/b/{client.blog_slug}" if client.blog_slug else None),
        redes_activas=client.redes_activas,
    )


@router.patch("/{client_id}", response_model=ClientResponse)
async def actualizar_cliente(
    client_id: int, data: ClientUpdate, db: AsyncSession = Depends(get_db)
):
    """Actualiza campos de un cliente."""
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(client, key, value)

    await db.flush()
    await db.refresh(client)

    return ClientResponse(
        id=client.id,
        nombre=client.nombre,
        email=client.email,
        industria=client.industria,
        sitio_web=client.sitio_web,
        plan=client.plan,
        estado=client.estado,
        blog_slug=client.blog_slug,
        blog_domain=client.blog_domain,
        blog_url=f"https://{client.blog_domain}" if client.blog_domain else (f"https://blogengine.app/b/{client.blog_slug}" if client.blog_slug else None),
        redes_activas=client.redes_activas,
    )


@router.post("/{client_id}/cms")
async def configurar_cms(
    client_id: int, data: CMSCredentials, db: AsyncSession = Depends(get_db)
):
    """Configura las credenciales de CMS del cliente (encriptadas)."""
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Encriptar credenciales
    import json
    creds = {
        "username": data.username,
        "password": data.password,
        "api_key": data.api_key,
        "api_token": data.api_token,
    }
    client.cms_type = data.cms_type
    client.cms_url = data.cms_url
    client.cms_credentials_encrypted = encriptar(json.dumps(creds))

    await db.flush()
    return {"status": "ok", "mensaje": f"CMS {data.cms_type} configurado para {client.nombre}"}


@router.post("/{client_id}/social")
async def configurar_red_social(
    client_id: int, data: SocialCredentials, db: AsyncSession = Depends(get_db)
):
    """Configura credenciales de una red social (encriptadas)."""
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Mapeo de plataforma a campos del modelo
    token_fields = {
        "facebook": ("facebook_page_id", "facebook_token_encrypted"),
        "instagram": ("instagram_account_id", "instagram_token_encrypted"),
        "linkedin": ("linkedin_org_id", "linkedin_token_encrypted"),
        "twitter": ("twitter_user_id", "twitter_token_encrypted"),
        "pinterest": ("pinterest_board_id", "pinterest_token_encrypted"),
        "google_business": ("google_business_location_id", "google_business_token_encrypted"),
    }

    if data.plataforma not in token_fields:
        raise HTTPException(status_code=400, detail=f"Plataforma no soportada: {data.plataforma}")

    id_field, token_field = token_fields[data.plataforma]
    if data.account_id:
        setattr(client, id_field, data.account_id)
    setattr(client, token_field, encriptar(data.access_token))

    await db.flush()
    return {
        "status": "ok",
        "mensaje": f"{data.plataforma} configurado para {client.nombre}",
    }


@router.delete("/{client_id}")
async def eliminar_cliente(client_id: int, db: AsyncSession = Depends(get_db)):
    """Elimina un cliente (soft delete - cambia estado a 'cancelado')."""
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    client.estado = "cancelado"
    await db.flush()
    return {"status": "ok", "mensaje": f"Cliente '{client.nombre}' cancelado"}
