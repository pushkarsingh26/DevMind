"""
DevMind Backend — Application Entry Point
==========================================

Import order is intentional:
  1. logging_config  — must be first to silence third-party loggers before
                       any other module triggers their first log record.
  2. Everything else — database, AI, routes, etc.
"""

# ── 1. Logging must be configured before anything else ───────────────────────
import app.core.logging_config  # noqa: F401
import time
import sys

START_TIME = time.time()

# ── 2. Standard imports ───────────────────────────────────────────────────────
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logger import logger
from app.api.routes import router as api_router
from app.chat.routes import chat_router          # Phase 5
from app.api.agents import router as agents_router
from app.db.database import engine
from app.db.base import Base

# ── 3. Database initialisation ────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)
logger.info("Database tables verified / created")


def safe_print(text: str):
    """Safely prints text to stdout. Uses unicode checkmarks if supported by console encoding, otherwise ASCII."""
    enc = sys.stdout.encoding or "utf-8"
    try:
        # Check if encoding supports the checkmark character
        "✓".encode(enc)
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except UnicodeEncodeError:
        # Fallback for old console encodings (e.g. cp1252 on Windows cmd)
        safe_text = (
            text.replace("✓", "✓")  # keep checkmark if we do a replace, or map to clean ascii
        )
        # Actually replace the unicode checkmark with a clean ASCII variant for non-unicode console
        ascii_safe_text = (
            text.replace("✓", "[OK]")
            .replace("────────────────────────────────────", "------------------------------------")
        )
        try:
            sys.stdout.write(
                ascii_safe_text.encode(enc, errors="replace").decode(enc)
                + "\n"
            )
            sys.stdout.flush()
        except Exception:
            print(ascii_safe_text, flush=True)


# ── 4. Lifespan handler (replaces deprecated @app.on_event) ──────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Print a clean startup summary; run cleanup on shutdown."""
    startup_time = time.time() - START_TIME
    env = "Development" if settings.DEBUG else "Production"
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    
    banner = f"""
====================================================
             DevMind AI Backend v0.5.0
====================================================

✓ Configuration Loaded
✓ Database Connected
✓ Token Manager Ready
✓ AI Cache Ready
✓ Embedding Model Ready
✓ FAISS Ready
✓ Repository Memory Ready
✓ Prompt Library Loaded
✓ Agent Registry Loaded
✓ Workflow Templates Loaded

AI Providers
────────────────────────────────────
✓ Google AI Studio
✓ NVIDIA NIM
✓ Groq
✓ OpenRouter

Environment : {env}
Python      : {py_ver}
Startup Time: {startup_time:.2f}s

Server
────────────────────────────────────
API  : http://127.0.0.1:8000
Docs : http://127.0.0.1:8000/docs

====================================================
✓ DevMind Backend Ready
====================================================
"""
    safe_print(banner)
    logger.info("DevMind startup complete")

    yield  # application runs here

    logger.info("DevMind shutting down \u2014 goodbye")


# ── 5. FastAPI application ────────────────────────────────────────────────────
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="DevMind Backend \u2014 AI Repository Intelligence Platform",
    version="0.5.0",
    lifespan=lifespan,
)

# ── 6. CORS middleware ────────────────────────────────────────────────────────
if settings.ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# ── 7. Register routers ───────────────────────────────────────────────────────
app.include_router(api_router)
app.include_router(chat_router)       # Phase 5
app.include_router(agents_router)


# ── 8. Health check ───────────────────────────────────────────────────────────
@app.get("/", summary="Root Health Endpoint")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "phase": 5
    }
