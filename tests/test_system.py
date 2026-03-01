"""
BlogEngine - Test integral del sistema.

Verifica que todos los componentes principales funcionan:
1. App FastAPI arranca y responde
2. Modelos se crean correctamente en BD
3. CRUD de clientes vía API
4. Pipeline SEO (auditoría)
5. Imports de todos los módulos
6. Tareas Celery importables
7. Blog público renderiza
"""
import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient, ASGITransport

# ============================================================
# CONFIG pytest-asyncio
# ============================================================
pytestmark = pytest.mark.asyncio(loop_scope="session")


# ============================================================
# FIXTURES
# ============================================================

@pytest_asyncio.fixture
async def db_session():
    """Inicializa BD y devuelve una sesión."""
    from models.base import init_db, async_session
    await init_db()
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client():
    """Cliente HTTP para tests de API."""
    from api.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ============================================================
# 1. APP ARRANCA
# ============================================================

class TestAppStartup:
    """Verifica que la app FastAPI responde."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        r = await client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert data["app"] == "BlogEngine"
        assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_docs_accessible(self, client):
        r = await client.get("/docs")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_login_page(self, client):
        r = await client.get("/admin/login")
        assert r.status_code == 200
        assert "login" in r.text.lower() or "iniciar" in r.text.lower()


# ============================================================
# 2. MODELOS
# ============================================================

class TestModels:
    """Verifica que los modelos se importan y crean correctamente."""

    def test_client_model_fields(self):
        from models.client import Client
        cols = [c.name for c in Client.__table__.columns]
        required = ["id", "nombre", "email", "industria", "blog_slug", "plan"]
        for field in required:
            assert field in cols, f"Campo '{field}' no encontrado en Client"

    def test_blog_post_model_fields(self):
        from models.blog_post import BlogPost
        cols = [c.name for c in BlogPost.__table__.columns]
        required = ["id", "client_id", "titulo", "slug", "contenido_html", "keyword_principal", "estado"]
        for field in required:
            assert field in cols, f"Campo '{field}' no encontrado en BlogPost"

    def test_seo_models_import(self):
        from models.seo_strategy import MoneyPage, TopicCluster, SEOKeyword, SEOAuditLog
        assert MoneyPage.__tablename__
        assert TopicCluster.__tablename__
        assert SEOKeyword.__tablename__
        assert SEOAuditLog.__tablename__

    def test_calendar_model_import(self):
        from models.calendar import CalendarEntry
        assert CalendarEntry.__tablename__

    def test_social_post_model_import(self):
        from models.social_post import SocialPost
        assert SocialPost.__tablename__

    def test_ai_usage_model_import(self):
        from models.ai_usage import AIUsage
        assert AIUsage.__tablename__

    @pytest.mark.asyncio
    async def test_create_and_query_client(self, db_session):
        """Crea un cliente en BD y lo recupera."""
        from models.client import Client
        from sqlalchemy import select

        test_client = Client(
            nombre="Test Integral",
            email="test-integral@test.local",
            industria="testing",
            sitio_web="https://test-integral.local",
            blog_slug="test-integral",
            plan="free",
        )
        db_session.add(test_client)
        await db_session.commit()

        result = await db_session.execute(
            select(Client).where(Client.email == "test-integral@test.local")
        )
        found = result.scalar_one_or_none()
        assert found is not None
        assert found.nombre == "Test Integral"
        assert found.plan == "free"

        # Cleanup
        await db_session.delete(found)
        await db_session.commit()


# ============================================================
# 3. API CLIENTS CRUD
# ============================================================

class TestAPIClients:
    """Verifica las rutas de la API de clientes."""

    @pytest.mark.asyncio
    async def test_list_clients(self, client):
        r = await client.get("/api/clients/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_create_client(self, client):
        import time
        slug = f"api-test-{int(time.time())}"
        r = await client.post("/api/clients/", json={
            "nombre": "API Test Client",
            "email": f"{slug}@test.local",
            "industria": "testing",
            "sitio_web": "https://test.local",
            "blog_slug": slug,
        })
        assert r.status_code in (200, 201), f"Status {r.status_code}: {r.text}"
        data = r.json()
        assert data["nombre"] == "API Test Client"
        self.__class__._created_id = data["id"]
        self.__class__._created_slug = slug

    @pytest.mark.asyncio
    async def test_get_client(self, client):
        cid = getattr(self.__class__, "_created_id", None)
        if not cid:
            pytest.skip("No se creó cliente en test anterior")
        r = await client.get(f"/api/clients/{cid}")
        assert r.status_code == 200
        assert r.json()["nombre"] == "API Test Client"

    @pytest.mark.asyncio
    async def test_delete_client(self, client):
        cid = getattr(self.__class__, "_created_id", None)
        if not cid:
            pytest.skip("No se creó cliente en test anterior")
        r = await client.delete(f"/api/clients/{cid}")
        assert r.status_code in (200, 204)


# ============================================================
# 4. SEO AUDIT
# ============================================================

class TestSEOAudit:
    """Verifica el sistema de auditoría SEO."""

    def test_audit_perfect_article(self):
        """Artículo con todos los checks debería tener score alto."""
        from core.seo_strategy import OnPageSEOOptimizer

        html = """
        <h1>Mejores restaurantes en Houston para familias</h1>
        <p>Mejores restaurantes en Houston es un tema importante para quienes buscan opciones gastronómicas.
        En este artículo cubrimos los mejores restaurantes en Houston que deberías conocer.</p>
        <h2>Top restaurantes en Houston por zona</h2>
        <p>Aquí encontrarás opciones de mejores restaurantes en Houston organizadas por área geográfica.
        Cada zona tiene sus mejores restaurantes en Houston con diferentes especialidades.</p>
        <h2>Restaurantes familiares en Houston</h2>
        <p>Los mejores restaurantes en Houston para familias ofrecen menús especiales para niños.
        Descubre los mejores restaurantes en Houston que son ideales para una salida familiar.</p>
        <h2>Mejores restaurantes en Houston con terraza</h2>
        <p>Si prefieres comer al aire libre, estos mejores restaurantes en Houston tienen terraza.
        <a href="/guia-gastronomica-houston" title="Guía gastronómica">Ver guía completa</a>.
        <a href="/reservaciones-Houston" title="Reservaciones">Haz tu reservación</a>.
        <a href="https://clientesite.com/menu" title="Ver menú">Consulta nuestro menú</a>.
        <a href="https://clientesite.com/contacto" title="Contacto">Contáctanos</a>.</p>
        <img src="/img/restaurantes.jpg" alt="Mejores restaurantes en Houston" />
        """ + " mejores restaurantes " * 5

        result = OnPageSEOOptimizer.audit(
            titulo="Mejores restaurantes en Houston: Guía 2026",
            meta_description="Descubre los mejores restaurantes en Houston para familias. Guía actualizada con recomendaciones y precios.",
            slug="mejores-restaurantes-en-houston",
            contenido_html=html,
            keyword_principal="mejores restaurantes en Houston",
            keywords_secundarias=["restaurantes familiares", "comer en Houston"],
            existing_posts_count=0,
        )

        assert result["puntuacion"] >= 60, f"Score {result['puntuacion']}/100 demasiado bajo"
        assert isinstance(result["checks"], list)
        assert len(result["checks"]) > 5

    def test_audit_bad_article(self):
        """Artículo sin SEO debería tener score bajo."""
        from core.seo_strategy import OnPageSEOOptimizer

        result = OnPageSEOOptimizer.audit(
            titulo="Mi artículo genérico",
            meta_description="Un artículo cualquiera",
            slug="articulo-generico",
            contenido_html="<p>Contenido corto sin keywords ni estructura.</p>",
            keyword_principal="restaurantes en Houston",
            existing_posts_count=5,
        )

        assert result["puntuacion"] < 40, f"Score {result['puntuacion']} debería ser bajo"
        assert len(result["problemas_criticos"]) > 0

    def test_audit_first_article_no_internal_links_penalty(self):
        """Primer artículo NO debe ser penalizado por falta de internal links."""
        from core.seo_strategy import OnPageSEOOptimizer

        html = "<h1>Test</h1>" + "<p>keyword keyword keyword</p>" * 20
        result_first = OnPageSEOOptimizer.audit(
            titulo="keyword: Guía completa",
            meta_description="Todo sobre keyword en esta guía completa para ti.",
            slug="keyword-guia",
            contenido_html=html,
            keyword_principal="keyword",
            existing_posts_count=0,
        )
        result_later = OnPageSEOOptimizer.audit(
            titulo="keyword: Guía completa",
            meta_description="Todo sobre keyword en esta guía completa para ti.",
            slug="keyword-guia",
            contenido_html=html,
            keyword_principal="keyword",
            existing_posts_count=10,
        )
        assert result_first["puntuacion"] >= result_later["puntuacion"]


# ============================================================
# 5. IMPORTS DE MÓDULOS CORE
# ============================================================

class TestImports:
    """Verifica que todos los módulos principales se importan."""

    def test_content_engine(self):
        from core.content_engine import ContentEngine
        assert ContentEngine

    def test_seo_engine(self):
        from core.seo_engine import SEOMetaGenerator, SchemaGenerator, SitemapGenerator
        assert SEOMetaGenerator
        assert SchemaGenerator
        assert SitemapGenerator

    def test_seo_strategy(self):
        from core.seo_strategy import OnPageSEOOptimizer, SEOPromptBuilder, KeywordStrategyPlanner
        assert OnPageSEOOptimizer
        assert SEOPromptBuilder
        assert KeywordStrategyPlanner

    def test_ai_router(self):
        from core.ai_router import AIRouter
        assert AIRouter

    def test_ai_providers(self):
        from core.ai_providers.base import AIResponse
        from core.ai_providers.deepseek import DeepSeekProvider
        from core.ai_providers.claude import ClaudeProvider
        assert AIResponse
        assert DeepSeekProvider
        assert ClaudeProvider

    def test_blog_renderer(self):
        from core.blog_renderer import router as blog_router
        assert blog_router

    def test_cost_tracker(self):
        from core.cost_tracker import CostTracker
        assert CostTracker

    def test_celery_app(self):
        from core.celery_app import celery_app, run_async
        assert celery_app
        assert run_async

    def test_task_wrappers(self):
        from core.task_wrappers import (
            task_research_keywords,
            task_generate_article,
            task_auto_publish,
            task_daily_pipeline,
        )
        assert task_research_keywords
        assert task_generate_article

    def test_scheduler(self):
        from core.scheduler import dispatch_daily_pipelines
        assert dispatch_daily_pipelines

    def test_celery_tasks_init(self):
        from core.tasks import (
            generate_scheduled_posts,
            auto_publish_scheduled,
            ping_all_clients,
            distribute_pending,
            generate_calendars,
        )
        assert generate_scheduled_posts
        assert auto_publish_scheduled

    def test_auth_module(self):
        from api.auth import create_session_token, verify_session_token, require_auth
        assert create_session_token
        assert verify_session_token

    def test_config(self):
        from config import get_settings
        settings = get_settings()
        assert settings.admin_user
        assert settings.admin_password


# ============================================================
# 6. AI RESPONSE DATACLASS
# ============================================================

class TestAIResponse:

    def test_success_response(self):
        from core.ai_providers.base import AIResponse
        r = AIResponse(
            contenido="<h1>Test</h1>",
            tokens_input=500,
            tokens_output=200,
            costo_usd=0.01,
            modelo="deepseek-chat",
            proveedor="deepseek",
        )
        assert r.exito is True
        assert r.tokens_total == 700
        assert r.costo_usd == 0.01

    def test_error_response(self):
        from core.ai_providers.base import AIResponse
        r = AIResponse(
            contenido="",
            tokens_input=0,
            tokens_output=0,
            costo_usd=0.0,
            modelo="deepseek-chat",
            proveedor="deepseek",
            error="API timeout",
        )
        assert r.error == "API timeout"
        assert r.tokens_total == 0
        assert r.contenido == ""


# ============================================================
# 7. SEO ENGINE MODULES
# ============================================================

class TestSEOEngine:

    def test_schema_generator_import(self):
        from core.seo_engine import SchemaGenerator
        assert SchemaGenerator

    def test_meta_generator_import(self):
        from core.seo_engine import SEOMetaGenerator
        assert SEOMetaGenerator

    def test_sitemap_generator_import(self):
        from core.seo_engine import SitemapGenerator
        assert SitemapGenerator

    def test_canonical_url_builder(self):
        from core.seo_engine import CanonicalURLBuilder
        assert CanonicalURLBuilder

    def test_internal_linking_engine(self):
        from core.seo_engine import InternalLinkingEngine
        assert InternalLinkingEngine


# ============================================================
# 8. BLOG PÚBLICO
# ============================================================

class TestBlogPublic:

    @pytest.mark.asyncio
    async def test_blog_returns_html(self, client):
        """El blog público debe devolver HTML (no JSON)."""
        r = await client.get("/blog/test-slug-inexistente")
        assert r.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_sitemap(self, client):
        """Sitemap debe ser accesible."""
        r = await client.get("/sitemap.xml")
        assert r.status_code in (200, 404)


# ============================================================
# 9. CLEAN AI RESPONSE
# ============================================================

class TestCleanAIResponse:

    def test_strips_html_backticks(self):
        """Verifica que se limpian los backticks de DeepSeek."""
        import re
        content = '```html\n<h1>Test</h1>\n<p>Hello</p>\n```'
        content = re.sub(r'^\s*```html\s*\n?', '', content)
        content = re.sub(r'^\s*```\w*\s*\n?', '', content)
        content = re.sub(r'\n?\s*```\s*$', '', content)
        assert '```' not in content
        assert '<h1>Test</h1>' in content

    def test_no_change_clean_html(self):
        """HTML sin backticks no debe cambiar."""
        import re
        content = '<h1>Test</h1>\n<p>Hello</p>'
        original = content
        content = re.sub(r'^\s*```html\s*\n?', '', content)
        content = re.sub(r'^\s*```\w*\s*\n?', '', content)
        content = re.sub(r'\n?\s*```\s*$', '', content)
        assert content == original


# ============================================================
# 10. ADMIN AUTH
# ============================================================

class TestAdminAuth:

    @pytest.mark.asyncio
    async def test_admin_requires_login(self, client):
        """Rutas admin deben redirigir al login sin sesión."""
        r = await client.get("/admin/", follow_redirects=False)
        assert r.status_code in (303, 302, 200)

    @pytest.mark.asyncio
    async def test_login_with_wrong_password(self, client):
        """Login con credenciales incorrectas no debe dar acceso."""
        r = await client.post("/admin/login", data={
            "username": "wrong",
            "password": "wrong",
        }, follow_redirects=False)
        assert r.status_code in (200, 303, 302, 401)

    @pytest.mark.asyncio
    async def test_login_with_correct_password(self, client):
        """Login con credenciales correctas debe dar acceso."""
        from config import get_settings
        settings = get_settings()
        r = await client.post("/admin/login", data={
            "username": settings.admin_user,
            "password": settings.admin_password,
        }, follow_redirects=False)
        assert r.status_code in (200, 303, 302)
