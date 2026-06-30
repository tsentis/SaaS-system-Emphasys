"""Aggregate router for API v1. Feature routers are added per milestone."""

from fastapi import APIRouter

from app.api.v1 import auth, health, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth")
api_router.include_router(users.router, prefix="/users")

# Milestone 2+: api_router.include_router(documents.router, prefix="/documents")
#               api_router.include_router(projects.router, prefix="/projects")
#               …
