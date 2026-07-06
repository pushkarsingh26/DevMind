from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import router as api_router
from app.core.logger import logger

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="DevMind Backend - Phase 1 Foundation",
    version="0.1.0"
)

# Set CORS middleware
if settings.ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"CORS middleware configured for origins: {settings.ALLOWED_ORIGINS}")

# Register APIRouter paths
app.include_router(api_router)
logger.info("Routes loaded at root level")

@app.get("/", summary="Root Health Endpoint")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "phase": 1
    }
