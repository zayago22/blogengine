"""
BlogEngine Python Client.
Usado por las integraciones de Django, Flask y FastAPI.

pip install httpx

USO:
    client = BlogEngineClient("mi-empresa")
    posts = await client.get_posts()
    post = await client.get_post("slug-del-articulo")
"""
import httpx
from typing import Optional
from functools import lru_cache
import time
import logging

logger = logging.getLogger(__name__)


class BlogEngineClient:
    """Cliente HTTP para la API pública de BlogEngine."""

    def __init__(
        self,
        blog_slug: str,
        api_url: str = "https://blogengine.app",
        cache_ttl: int = 3600,
        timeout: int = 10,
    ):
        self.blog_slug = blog_slug
        self.api_url = api_url.rstrip("/")
        self.cache_ttl = cache_ttl
        self.timeout = timeout
        self._cache: dict = {}

    async def get_posts(self, limit: int = 20) -> list[dict]:
        """Obtiene lista de posts publicados."""
        return await self._fetch(
            f"/api/public/{self.blog_slug}/posts?limit={limit}"
        ) or []

    async def get_post(self, slug: str) -> Optional[dict]:
        """Obtiene un post individual por slug."""
        return await self._fetch(
            f"/api/public/{self.blog_slug}/posts/{slug}"
        )

    def get_posts_sync(self, limit: int = 20) -> list[dict]:
        """Versión síncrona para Django views tradicionales."""
        return self._fetch_sync(
            f"/api/public/{self.blog_slug}/posts?limit={limit}"
        ) or []

    def get_post_sync(self, slug: str) -> Optional[dict]:
        """Versión síncrona para Django views tradicionales."""
        return self._fetch_sync(
            f"/api/public/{self.blog_slug}/posts/{slug}"
        )

    async def _fetch(self, endpoint: str):
        """Fetch async con cache."""
        cached = self._get_cache(endpoint)
        if cached is not None:
            return cached

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.api_url}{endpoint}",
                    headers={"Accept": "application/json"},
                )
                if response.status_code == 200:
                    data = response.json()
                    self._set_cache(endpoint, data)
                    return data
                elif response.status_code == 404:
                    return None
        except Exception as e:
            logger.error(f"[BlogEngine] Error fetching {endpoint}: {e}")
        return None

    def _fetch_sync(self, endpoint: str):
        """Fetch síncrono con cache."""
        cached = self._get_cache(endpoint)
        if cached is not None:
            return cached

        try:
            response = httpx.get(
                f"{self.api_url}{endpoint}",
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
            if response.status_code == 200:
                data = response.json()
                self._set_cache(endpoint, data)
                return data
            elif response.status_code == 404:
                return None
        except Exception as e:
            logger.error(f"[BlogEngine] Error fetching {endpoint}: {e}")
        return None

    def _get_cache(self, key: str):
        entry = self._cache.get(key)
        if entry and time.time() - entry["time"] < self.cache_ttl:
            return entry["data"]
        return None

    def _set_cache(self, key: str, data):
        self._cache[key] = {"data": data, "time": time.time()}

    def clear_cache(self):
        self._cache.clear()


def render_seo_meta(post: dict, canonical_url: str, site_name: str = "") -> str:
    """Genera meta tags HTML para un artículo. Útil para cualquier framework."""
    tags = []
    title = post.get("titulo", "")
    desc = post.get("meta_description", "")
    image = post.get("imagen_destacada_url", "")
    date = post.get("fecha_publicado", "")

    full_title = f"{title} | {site_name}" if site_name else title

    tags.append(f'<title>{_esc(full_title)}</title>')
    tags.append(f'<meta name="description" content="{_esc(desc)}">')
    tags.append(f'<link rel="canonical" href="{canonical_url}">')
    tags.append(f'<meta property="og:title" content="{_esc(full_title)}">')
    tags.append(f'<meta property="og:description" content="{_esc(desc)}">')
    tags.append(f'<meta property="og:url" content="{canonical_url}">')
    tags.append(f'<meta property="og:type" content="article">')
    if image:
        tags.append(f'<meta property="og:image" content="{image}">')
    if date:
        tags.append(f'<meta property="article:published_time" content="{date}">')
    tags.append(f'<meta name="twitter:card" content="summary_large_image">')

    return "\n    ".join(tags)


def render_schema_article(post: dict, canonical_url: str, org_name: str, org_url: str) -> str:
    """Genera Schema.org Article JSON-LD."""
    import json
    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": post.get("titulo", ""),
        "description": post.get("meta_description", ""),
        "url": canonical_url,
        "datePublished": post.get("fecha_publicado", ""),
        "publisher": {"@type": "Organization", "name": org_name, "url": org_url},
    }
    if post.get("imagen_destacada_url"):
        schema["image"] = post["imagen_destacada_url"]
    return f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>'


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
