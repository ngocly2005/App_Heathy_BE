from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import router as auth_router
from app.core.config import get_settings
from app.profile import router as profile_router
from app.tracking import router as tracking_router
from app.weight import router as weight_router
from app.diary import router as diary_router
from app.saved_meals import router as saved_meals_router
from app.ai import router as ai_router
from app.settings import router as settings_router
from app.log_updates import router as log_updates_router
from app.admin import router as admin_router
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend",
)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
                   allow_headers=["Authorization", "Content-Type"])
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(profile_router, prefix=settings.api_v1_prefix)
app.include_router(tracking_router, prefix=settings.api_v1_prefix)
app.include_router(weight_router, prefix=settings.api_v1_prefix)
app.include_router(diary_router, prefix=settings.api_v1_prefix)
app.include_router(saved_meals_router, prefix=settings.api_v1_prefix)
app.include_router(ai_router, prefix=settings.api_v1_prefix)
app.include_router(settings_router, prefix=settings.api_v1_prefix)
app.include_router(log_updates_router, prefix=settings.api_v1_prefix)
app.include_router(admin_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "environment": settings.environment,
    }
