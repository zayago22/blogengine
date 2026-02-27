"""
Celery tasks for social media distribution.
Beat schedule: every 2 hours (distribute_pending)
"""
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

from core.celery_app import celery_app, run_async
from models.base import async_session

logger = logging.getLogger("blogengine.tasks.social")


# ---------------------------------------------------------------------------
# HTML → plain text helper
# ---------------------------------------------------------------------------

class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str):
        self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts)


def _strip_html(html: str) -> str:
    """Return plain text from HTML, collapsing whitespace."""
    if not html:
        return ""
    stripper = _HTMLStripper()
    stripper.feed(html)
    text = stripper.get_text()
    # Collapse multiple spaces/newlines
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _clean_json(raw: str) -> str:
    """Strip markdown code fences if present."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        lines = lines[1:] if lines[0].startswith("```") else lines
        lines = lines[:-1] if lines and lines[-1].strip() == "```" else lines
        raw = "\n".join(lines).strip()
    return raw


# ---------------------------------------------------------------------------
# Core async logic
# ---------------------------------------------------------------------------

PLATAFORMAS = ["facebook", "instagram", "linkedin", "twitter", "pinterest", "google_business"]


def _build_prompt(post, blog_slug: str, base_url: str, industria: str) -> str:
    resumen = _strip_html(post.contenido_html or "")[:300]
    url = f"{base_url}/b/{blog_slug}/{post.slug}"
    return (
        f"Genera copies para redes sociales de este artículo:\n\n"
        f"Título: {post.titulo}\n"
        f"Keyword: {post.keyword_principal or ''}\n"
        f"URL: {url}\n"
        f"Resumen: {resumen}\n"
        f"Industria: {industria}\n\n"
        f"Genera un copy para CADA plataforma:\n"
        f"1. Facebook: 2-3 párrafos, emoji moderado, CTA\n"
        f"2. Instagram: caption + 20-30 hashtags relevantes\n"
        f"3. LinkedIn: tono profesional, dato interesante, CTA\n"
        f"4. Twitter/X: máximo 280 chars, gancho fuerte, 3-5 hashtags\n"
        f"5. Pinterest: descripción para pin, keywords naturales\n"
        f"6. Google Business: 1 párrafo corto, CTA local\n\n"
        f'Responde SOLO en JSON válido:\n'
        f'{{"copies": [{{"plataforma": "facebook", "contenido": "...", "hashtags": "..."}}]}}'
    )


async def _create_social_copies(post_id: int, delete_pending: bool = False):
    """Generate and persist social copies for a single BlogPost."""
    from models.blog_post import BlogPost
    from models.social_post import SocialPost
    from models.client import Client
    from core.ai_router import AIRouter
    from sqlalchemy import select, delete as sa_delete
    from config import settings

    base_url = getattr(settings, "blogengine_base_url", "http://localhost:8000")

    async with async_session() as session:
        # Load post
        result = await session.execute(select(BlogPost).where(BlogPost.id == post_id))
        post = result.scalar_one_or_none()
        if not post:
            logger.warning("[Celery] BlogPost %d no encontrado", post_id)
            return 0

        # Load client
        result = await session.execute(select(Client).where(Client.id == post.client_id))
        client = result.scalar_one_or_none()
        if not client:
            logger.warning("[Celery] Cliente %d no encontrado para post %d", post.client_id, post_id)
            return 0

        # Optionally delete existing pending social posts
        if delete_pending:
            await session.execute(
                sa_delete(SocialPost).where(
                    SocialPost.blog_post_id == post_id,
                    SocialPost.estado == "pendiente",
                )
            )
            await session.commit()

        # Build prompt and call AI
        prompt = _build_prompt(post, client.blog_slug, base_url, client.industria)
        ai_router = AIRouter()

        try:
            raw_response = await ai_router.generate(
                task_name="copies_redes_sociales",
                prompt=prompt,
                session=session,
            )
            cleaned = _clean_json(raw_response)
            data = json.loads(cleaned)
            copies = data.get("copies", [])
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.error("[Celery] JSON parsing falló para post %d: %s", post_id, exc)
            return 0

        created = 0
        for copy in copies:
            plataforma = copy.get("plataforma", "").lower()
            if plataforma not in PLATAFORMAS:
                continue

            hashtags_raw = copy.get("hashtags", "")
            # Normalise hashtags to a list
            if isinstance(hashtags_raw, str):
                hashtags_list = [h.strip() for h in hashtags_raw.split() if h.strip()]
            elif isinstance(hashtags_raw, list):
                hashtags_list = hashtags_raw
            else:
                hashtags_list = []

            social = SocialPost(
                client_id=post.client_id,
                blog_post_id=post_id,
                plataforma=plataforma,
                texto=copy.get("contenido", ""),
                hashtags=hashtags_list,
                link_url=f"{base_url}/b/{client.blog_slug}/{post.slug}",
                estado="pendiente",
            )
            session.add(social)
            created += 1

        await session.commit()
        logger.info("[Celery] Social copies para '%s': %d plataformas", post.titulo, created)
        return created


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@celery_app.task(name="distribute_pending")
def distribute_pending():
    """
    Runs every 2 hours.
    Finds posts published in the last 24h that have no social copies yet,
    and generates copies for each.
    """
    from models.blog_post import BlogPost
    from models.social_post import SocialPost
    from sqlalchemy import select

    async def _run():
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        async with async_session() as session:
            # Posts published in the last 24h
            result = await session.execute(
                select(BlogPost).where(
                    BlogPost.estado == "publicado",
                    BlogPost.fecha_publicado >= cutoff,
                )
            )
            posts = result.scalars().all()

            # Filter: only posts without existing SocialPosts
            posts_sin_social = []
            for post in posts:
                sp_result = await session.execute(
                    select(SocialPost.id).where(SocialPost.blog_post_id == post.id).limit(1)
                )
                if sp_result.scalar_one_or_none() is None:
                    posts_sin_social.append(post.id)

        logger.info("[Celery] distribute_pending: %d posts sin social copies", len(posts_sin_social))

        total = 0
        for post_id in posts_sin_social:
            try:
                count = await _create_social_copies(post_id, delete_pending=False)
                total += count
            except Exception as exc:
                logger.error("[Celery] Error generando social copies para post %d: %s", post_id, exc)

        logger.info("[Celery] distribute_pending completado: %d copies creados", total)

    run_async(_run())


@celery_app.task(name="generate_social_for_post")
def generate_social_for_post(post_id: int):
    """
    Generates social copies for a specific post.
    Deletes existing 'pendiente' copies before regenerating.
    """
    logger.info("[Celery] Generando social copies para post %d", post_id)

    async def _run():
        return await _create_social_copies(post_id, delete_pending=True)

    count = run_async(_run())
    logger.info("[Celery] Post %d: %d social copies creados", post_id, count)
    return {"post_id": post_id, "copies_creados": count}


@celery_app.task(name="publish_social_post")
def publish_social_post(social_post_id: int):
    """
    PLACEHOLDER — marks a SocialPost as published.
    Future integrations should replace the TODO sections.

    # TODO: Integrar Meta Graph API para Facebook/Instagram
    # TODO: Integrar LinkedIn API
    # TODO: Integrar Twitter/X API v2
    # TODO: Integrar Pinterest API
    # TODO: Integrar Google Business Profile API
    """
    from models.social_post import SocialPost
    from sqlalchemy import select

    async def _run():
        async with async_session() as session:
            result = await session.execute(
                select(SocialPost).where(SocialPost.id == social_post_id)
            )
            social = result.scalar_one_or_none()
            if not social:
                logger.warning("[Celery] SocialPost %d no encontrado", social_post_id)
                return {"success": False, "error": "not_found"}

            social.estado = "publicado"
            social.fecha_publicado = datetime.now(timezone.utc)
            await session.commit()
            logger.info(
                "[Celery] SocialPost %d (%s) marcado como publicado",
                social_post_id, social.plataforma,
            )
            return {"success": True, "social_post_id": social_post_id, "plataforma": social.plataforma}

    return run_async(_run())
