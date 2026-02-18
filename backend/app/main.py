import logging
import sqlite3
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import vault, jobs, captures, events, documents, tags, search, calendar, backup, analytics

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: migrate and integrity-check existing vault database
    if settings.db_path.exists():
        try:
            from app.database import MIGRATIONS
            conn = sqlite3.connect(str(settings.db_path))
            for migration in MIGRATIONS:
                try:
                    conn.execute(migration)
                    conn.commit()
                except sqlite3.OperationalError:
                    pass  # already applied
            result = conn.execute("PRAGMA integrity_check").fetchone()
            conn.close()
            if result and result[0] == "ok":
                logger.info("Database integrity check passed.")
            else:
                logger.error("DATABASE INTEGRITY CHECK FAILED: %s — vault may be corrupt.", result)
        except Exception as exc:
            logger.error("Could not run startup migration/integrity check: %s", exc)
    yield
    # Shutdown: lock the vault
    from app.services.vault_service import vault_service
    vault_service.lock()


app = FastAPI(
    title="Application Vault",
    description="Local-first job application archive and document vault",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # Security: restrict CORS to local dev origins and browser extension origins.
    # moz-extension:// and chrome-extension:// are only reachable by locally
    # installed extensions, so allowing them does not expose the API to the internet.
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_origin_regex=r"(moz-extension|chrome-extension)://[a-zA-Z0-9-]+",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vault.router, prefix=settings.api_prefix)
app.include_router(jobs.router, prefix=settings.api_prefix)
app.include_router(captures.router, prefix=settings.api_prefix)
app.include_router(events.router, prefix=settings.api_prefix)
app.include_router(documents.router, prefix=settings.api_prefix)
app.include_router(tags.router, prefix=settings.api_prefix)
app.include_router(tags.tag_jobs_router, prefix=settings.api_prefix)
app.include_router(search.router, prefix=settings.api_prefix)
app.include_router(calendar.router, prefix=settings.api_prefix)
app.include_router(backup.router, prefix=settings.api_prefix)
app.include_router(analytics.router, prefix=settings.api_prefix)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
