"""Aggregate router for API v1. Feature routers are added per milestone."""

from fastapi import APIRouter

from app.api.v1 import (
    analytics,
    apikeys,
    audit,
    auth,
    billing,
    documents,
    enrichment,
    export,
    gdpr,
    health,
    integrations,
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
api_router.include_router(enrichment.router, prefix="/projects")
api_router.include_router(organizations.router, prefix="/organizations")
api_router.include_router(search.router, prefix="/search")
api_router.include_router(analytics.router, prefix="/analytics")
api_router.include_router(export.router, prefix="/export")
api_router.include_router(apikeys.router, prefix="/api-keys")
api_router.include_router(integrations.router, prefix="/integrations")
api_router.include_router(gdpr.router, prefix="/gdpr")
api_router.include_router(audit.router, prefix="/audit")
api_router.include_router(billing.router, prefix="/billing")
