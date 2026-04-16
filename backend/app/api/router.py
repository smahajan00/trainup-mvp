from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.drills import router as drills_router
from app.api.routes.health import router as health_router
from app.api.routes.profile import router as profile_router
from app.api.routes.sports import router as sports_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(drills_router)
api_router.include_router(health_router, tags=["health"])
api_router.include_router(profile_router)
api_router.include_router(sports_router)
