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
import asyncio
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
from app.api.provider_routes import router as provider_router
from app.chat.routes import chat_router          # Phase 5
from app.api.workflows import router as workflows_router
from app.api.knowledge_graph import router as knowledge_graph_router  # Phase 8.2
from app.api.repository_analysis import router as repository_analysis_router
from app.api.planning import router as planning_router
from app.api.execution import router as execution_router
from app.api.collaboration import router as collaboration_router  # Phase 8.6
from app.api.memory import router as memory_router  # Phase 8.7 Memory Engine
from app.api.reasoning import router as reasoning_router  # Phase 8.8 Reasoning Engine
from app.api.decision import router as decision_router  # Phase 8.9 Decision Engine
from app.db.base import Base
from app.db.database import engine

# ── 3. Database initialisation ────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)
logger.info("Database tables verified / created")

# Migrate/add new columns to workflow_executions if they do not exist
try:
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if inspector.has_table("workflow_executions"):
        columns = [col["name"] for col in inspector.get_columns("workflow_executions")]
        with engine.begin() as conn:
            for col_name, col_def in [
                ("progress", "INTEGER DEFAULT 0"),
                ("current_step", "VARCHAR(255)"),
                ("summary", "TEXT"),
                ("telemetry", "TEXT"),
                ("report_path", "VARCHAR(512)"),
                ("logs_path", "VARCHAR(512)"),
                ("graph_path", "VARCHAR(512)"),
                ("diff_path", "VARCHAR(512)"),
                ("telemetry_path", "VARCHAR(512)"),
            ]:
                if col_name not in columns:
                    conn.execute(text(f"ALTER TABLE workflow_executions ADD COLUMN {col_name} {col_def}"))
                    logger.info(f"Dynamically added column '{col_name}' to 'workflow_executions'")
except Exception as e:
    logger.error(f"Failed to check/run database dynamic column updates: {e}")
# Dynamic column addition for repositories.intelligence_path
try:
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if inspector.has_table("repositories"):
        columns = [col["name"] for col in inspector.get_columns("repositories")]
        if "intelligence_path" not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE repositories ADD COLUMN intelligence_path VARCHAR(512)"))
                logger.info("Added column 'intelligence_path' to 'repositories'")
except Exception as e:
    logger.error(f"Failed to add intelligence_path column: {e}")


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
    from app.core.console import console
    from app.ai.provider_registry import provider_registry
    import os
    import shutil

    # Clean temporary workflow directories on startup
    try:
        temp_workflows_dir = os.path.join(str(settings.WORKSPACE_ROOT), "workflows")
        if os.path.exists(temp_workflows_dir):
            shutil.rmtree(temp_workflows_dir, ignore_errors=True)
            logger.info("Cleaned temporary workflow directories on startup")
    except Exception as e:
        logger.error(f"Failed to clean temporary workflow directories on startup: {e}")
    
    # Perform startup validation synchronously during initialization so we have full health data
    try:
        await provider_registry.validate_all()
    except Exception as e:
        logger.error(f"Failed to run startup provider validations: {e}")

    startup_time = time.time() - START_TIME
    env = "Development" if settings.DEBUG else "Production"
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    
    # Prepare provider statuses list for the banner
    all_statuses = provider_registry.get_all_statuses()
    providers_list = [
        {"name": "Google AI Studio", "status": all_statuses.get("google", {}).get("status", "unavailable")},
        {"name": "OpenRouter", "status": all_statuses.get("openrouter", {}).get("status", "unavailable")},
        {"name": "NVIDIA NIM", "status": all_statuses.get("nvidia", {}).get("status", "unavailable")},
        {"name": "Groq", "status": all_statuses.get("groq", {}).get("status", "unavailable")},
    ]

    console.display_startup_banner(env, py_ver, startup_time, providers_list)
    
    # Display the validation table
    validation_records = []
    for prov_key, stats in all_statuses.items():
        name_map = {
            "google": "Google",
            "groq": "Groq",
            "openrouter": "OpenRouter",
            "nvidia": "NVIDIA"
        }
        validation_records.append({
            "name": name_map.get(prov_key, prov_key.capitalize()),
            "status": stats["status"],
            "configured_model": stats["configured_model"],
            "resolved_model": stats["selected_model"],
            "latency": stats["latency"],
            "fallback": stats["fallback"]
        })
    console.display_provider_validation(validation_records)
    logger.info("DevMind startup complete")

    yield  # application runs here

    logger.info("DevMind shutting down — goodbye")


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
app.include_router(provider_router)   # Phase 7.5.2 — Provider diagnostics
app.include_router(chat_router)       # Phase 5
app.include_router(workflows_router)
app.include_router(knowledge_graph_router)  # Phase 8.2 — Knowledge Graph
app.include_router(repository_analysis_router)
app.include_router(planning_router)
app.include_router(execution_router)
app.include_router(collaboration_router)  # Phase 8.6 — Multi-Agent Collaboration
app.include_router(memory_router)     # Phase 8.7 — Memory & Learning Engine
app.include_router(reasoning_router)  # Phase 8.8 — Autonomous Reasoning Engine
app.include_router(decision_router)   # Phase 8.9 — Decision Engine


# ── 8. Health check ───────────────────────────────────────────────────────────
@app.get("/", summary="Root Health Endpoint")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "phase": 5
    }
