from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .body_limit import BodyLimitMiddleware
from .db import init_db
from .routers import auth, knowledge, people, sources

@asynccontextmanager
async def lifespan(_):
    init_db()
    yield


app = FastAPI(title="ContinuityOS API", version="0.1.0", lifespan=lifespan)
app.add_middleware(BodyLimitMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"], allow_credentials=False)
for r in (auth.router, sources.router, knowledge.router, people.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/ready")
def ready():
    from sqlalchemy import text
    from .db import SessionLocal
    from fastapi import HTTPException
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            db.execute(text("SELECT id FROM projects LIMIT 1"))
    except Exception:
        raise HTTPException(503, "Database is not ready") from None
    return {"status": "ready", "schema_migration_verified": False}
