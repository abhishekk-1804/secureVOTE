"""
SecureVOTE Backend â€” FastAPI Application Entry Point.

This is a research-oriented prototype of an election integrity pipeline.
It is NOT certified election equipment, production election infrastructure,
or legally compliant software.

See docs/limitations.md for a full list of known limitations.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize DB on startup, close on shutdown."""
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="SecureVOTE API",
    description=(
        "Educational/research prototype of an embedded electronic-voting "
        "and election-integrity pipeline. This is NOT production election "
        "infrastructure. See /docs for the interactive API explorer."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS â€” allow dashboard dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and register routers
from app.routers import auth, elections, votes, devices, audit, results  # noqa: E402

app.include_router(auth.router)
app.include_router(elections.router)
app.include_router(votes.router)
app.include_router(devices.router)
app.include_router(audit.router)
app.include_router(results.router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "securevote-backend"}
