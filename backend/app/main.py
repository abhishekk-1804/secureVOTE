"""
SecureVOTE Backend Ã¢â‚¬â€ FastAPI Application Entry Point.

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

# CORS Ã¢â‚¬â€ allow dashboard dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://secure-vote-eta.vercel.app",
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and register routers
from app.routers import auth, elections, votes, devices, audit, results, websockets, signing, anchors, anomalies, rfid, voters, complaints, polling_stations, simulation, transparency, geography, overseas  # noqa: E402

app.include_router(auth.router)
app.include_router(elections.router)
app.include_router(votes.router)
app.include_router(devices.router)
app.include_router(audit.router)
app.include_router(results.router)
app.include_router(websockets.router)
app.include_router(signing.router)
app.include_router(signing.election_signing_router)
app.include_router(anchors.router)
app.include_router(anchors.election_anchor_router)
app.include_router(anomalies.router)
app.include_router(rfid.router)
app.include_router(voters.router)
app.include_router(complaints.router)
app.include_router(polling_stations.router)
app.include_router(simulation.router)
app.include_router(transparency.router)
app.include_router(geography.router)
app.include_router(overseas.router)



@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "securevote-backend"}
