import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.mlflow_monitoring.mlflow_setup import init_mlflow
from app.routers import (
    chat,
    chatbot,
    dictionary,
    feedback,
    health,
    query,
    scenario,
    sessions,
)
from app.services import dictionary_service
from app.services.dictionary_service import generate_dictionary

logger = logging.getLogger(__name__)


async def _warm_up(app: FastAPI) -> None:
    """Run heavy startup tasks in the background so the health probe can respond immediately."""
    try:
        logger.info("Generating data dictionary from metadata + Delta table ...")
        local_dictionary = await generate_dictionary()
        dictionary_service.set_local_dictionary(local_dictionary)
        logger.info(
            "Dictionary ready: %d columns in %d themes",
            local_dictionary.total_columns,
            len(local_dictionary.themes),
        )
        app.state.ready = True
    except Exception:
        logger.exception("Background warm-up failed")


def _activate_faq_cache_backend() -> None:
    """Phase 3/4: opt-in Postgres FAQ cache. Default 'memory' leaves the in-memory
    store active. Set FAQ_CACHE_BACKEND=postgres (and run the Alembic migration) to
    persist suggestions/published FAQs in the shared sessions DB."""
    if settings.FAQ_CACHE_BACKEND != "postgres":
        return
    try:
        from app.database import engine
        from app.services.chatbot.faq_cache import set_store
        from app.services.chatbot.faq_cache_sql import SqlFaqCache

        set_store(SqlFaqCache(engine))
        logger.info("FAQ cache backend: Postgres (SqlFaqCache)")
    except Exception:
        logger.exception("Failed to enable Postgres FAQ cache; staying in-memory")


def _activate_audit_backend() -> None:
    """Phase 6: opt-in Postgres audit trail (AUDIT_BACKEND=postgres)."""
    if settings.AUDIT_BACKEND != "postgres":
        return
    try:
        from app.database import engine
        from app.services.audit import set_store as set_audit_store
        from app.services.audit_sql import SqlAuditStore

        set_audit_store(SqlAuditStore(engine))
        logger.info("Audit backend: Postgres (SqlAuditStore)")
    except Exception:
        logger.exception("Failed to enable Postgres audit; staying in-memory")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_mlflow()
    _activate_faq_cache_backend()
    _activate_audit_backend()
    app.state.ready = False
    task = asyncio.create_task(_warm_up(app))
    yield
    task.cancel()


app = FastAPI(title="Ruimtelijke Assistent", lifespan=lifespan)

# CORS
origins = (
    settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS != "*" else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=settings.ALLOWED_ORIGINS != "*",
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routers
app.include_router(health.router)
app.include_router(dictionary.router)
app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(feedback.router)
app.include_router(query.router)
app.include_router(scenario.router)  # NEW: unified scenario engine (design doc §6)
app.include_router(chatbot.router)  # NEW: grounded Dutch knowledge chatbot + FAQs (Phase 1)
