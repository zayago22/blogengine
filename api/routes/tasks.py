"""
API endpoints for monitoring and manually triggering Celery tasks.
All endpoints require X-Admin-Key header.
"""
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from config import get_settings
from core.celery_app import celery_app

# ---------------------------------------------------------------------------
# Security dependency
# ---------------------------------------------------------------------------

async def verify_admin_key(x_admin_key: str = Header(...)):
    expected = get_settings().admin_key
    if not expected or x_admin_key != expected:
        raise HTTPException(status_code=403, detail="Admin key inválida")
    return True


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(
    prefix="/api/tasks",
    tags=["tasks"],
    dependencies=[Depends(verify_admin_key)],
)


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class GenerateSingleBody(BaseModel):
    client_id: int
    keyword_id: int


class SocialForPostBody(BaseModel):
    post_id: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/generate-all", status_code=202)
async def trigger_generate_all():
    """Queue the generate_scheduled_posts task."""
    from core.tasks.generation import generate_scheduled_posts
    result = generate_scheduled_posts.delay()
    return {"task_id": result.id, "task": "generate_scheduled_posts", "status": "queued"}


@router.post("/publish-scheduled", status_code=202)
async def trigger_publish_scheduled():
    """Queue the auto_publish_scheduled task."""
    from core.tasks.publishing import auto_publish_scheduled
    result = auto_publish_scheduled.delay()
    return {"task_id": result.id, "task": "auto_publish_scheduled", "status": "queued"}


@router.post("/ping-seo", status_code=202)
async def trigger_ping_seo():
    """Queue the ping_all_clients task."""
    from core.tasks.seo_ping import ping_all_clients
    result = ping_all_clients.delay()
    return {"task_id": result.id, "task": "ping_all_clients", "status": "queued"}


@router.post("/distribute-social", status_code=202)
async def trigger_distribute_social():
    """Queue the distribute_pending social task."""
    from core.tasks.social import distribute_pending
    result = distribute_pending.delay()
    return {"task_id": result.id, "task": "distribute_pending", "status": "queued"}


@router.get("/{task_id}/status")
async def get_task_status(task_id: str):
    """Return current status of a Celery task by ID."""
    result = celery_app.AsyncResult(task_id)
    response: dict[str, Any] = {
        "task_id": task_id,
        "status": result.status,
        "ready": result.ready(),
        "result": result.result if result.ready() else None,
    }
    if result.failed():
        response["error"] = str(result.result)
    return response


@router.post("/generate-single", status_code=202)
async def trigger_generate_single(body: GenerateSingleBody):
    """Queue article generation for a specific client + keyword."""
    from core.tasks.generation import generate_single_article
    result = generate_single_article.delay(body.client_id, body.keyword_id)
    return {
        "task_id": result.id,
        "task": "generate_single_article",
        "status": "queued",
        "client_id": body.client_id,
        "keyword_id": body.keyword_id,
    }


@router.post("/social-for-post", status_code=202)
async def trigger_social_for_post(body: SocialForPostBody):
    """Queue social copy generation for a specific post."""
    from core.tasks.social import generate_social_for_post
    result = generate_social_for_post.delay(body.post_id)
    return {
        "task_id": result.id,
        "task": "generate_social_for_post",
        "status": "queued",
        "post_id": body.post_id,
    }
