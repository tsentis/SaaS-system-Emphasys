"""Celery application. Tasks (PDF ingest → extract → store) are added in Milestone 3."""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "emphasys",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
)


@celery_app.task(name="ping")
def ping() -> str:
    """Smoke-test task to verify the worker is wired up."""
    return "pong"
