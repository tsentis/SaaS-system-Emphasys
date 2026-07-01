"""Aggregate router for API v1. Feature routers are added per milestone."""

from fastapi import APIRouter

from app.api.v1 import (
    analytics,
    auth,
    documents,
    health,
    organizations,
    projects,
    search,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth")
api_router.include_router(users.router, prefix="/users")
api_router.include_router(documents.router, prefix="/documents")
api_router.include_router(projects.router, prefix="/projects")
api_router.include_router(organizations.router, prefix="/organizations")
api_router.include_router(search.router, prefix="/search")
api_router.include_router(analytics.router, prefix="/analytics")
