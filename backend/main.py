# backend/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from routers import github, dashboard

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs on startup
    print("🚀 PulseAI starting up...")
    yield
    # Runs on shutdown
    print("🛑 PulseAI shutting down...")

app = FastAPI(
    title="PulseAI",
    description="Agent Swarm for Engineering Intelligence",
    version="0.1.0",
    lifespan=lifespan
)

# Register routers
app.include_router(github.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])

@app.get("/health")
async def health():
    return {"status": "ok", "service": "PulseAI"}