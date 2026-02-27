"""
BlogEngine - Aplicación principal FastAPI.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

from models.base import init_db
from utils.logger import setup_logging
from api.routes import clients, posts, publish, calendar, analytics, webhooks, seo, integrations
from api.routes.test_ai import router as test_ai_router
from api.routes.dashboard import router as dashboard_router
from api.routes.tasks import router as tasks_router
from core.blog_renderer import router as blog_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Eventos de inicio y cierre de la aplicación."""
    # Startup
    setup_logging()
    logger.info("BlogEngine iniciando...")
    await init_db()
    logger.info("Base de datos inicializada")
    yield
    # Shutdown
    logger.info("BlogEngine cerrando...")


app = FastAPI(
    title="BlogEngine",
    description="Plataforma de generación y distribución automática de blogs para clientes",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Templates ---
templates = Jinja2Templates(directory="templates")

# --- Rutas API ---
app.include_router(clients.router, prefix="/api/clients", tags=["Clientes"])
app.include_router(posts.router, prefix="/api/posts", tags=["Blog Posts"])
app.include_router(publish.router, prefix="/api/publish", tags=["Publicación"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["Calendario"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Webhooks"])
app.include_router(seo.router, prefix="/api/seo", tags=["SEO"])
app.include_router(integrations.router, prefix="/api/integrations", tags=["Integraciones"])
app.include_router(test_ai_router, prefix="/api/test", tags=["Test IA"])

# --- Dashboard Admin ---
app.include_router(dashboard_router, prefix="/admin", tags=["Admin Dashboard"])

# --- Tareas Celery ---
app.include_router(tasks_router)

# --- Blog público (sin prefix, se sirve en la raíz) ---
app.include_router(blog_router, tags=["Blog Público"])


@app.get("/")
async def root():
    """Endpoint raíz - info de la API."""
    return {
        "app": "BlogEngine",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok"}
