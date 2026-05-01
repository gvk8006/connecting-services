"""
Marketing Agency AI - Main FastAPI Application
Real-time lead generation platform powered by autonomous AI agents.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.routes import leads, agents, campaigns, dashboard, capture, marketplace
from app.services.orchestrator import orchestrator
from app.services.scheduler import start_scheduler, stop_scheduler
from app.services.websocket_manager import ws_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Marketing Agency AI...")
    await init_db()
    await orchestrator.initialize_default_agents()
    logger.info("Database initialized. Default agents ready.")
    start_scheduler(prospect_interval_hours=4)
    yield
    # Shutdown
    stop_scheduler()
    logger.info("Shutting down Marketing Agency AI...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(leads.router)
app.include_router(agents.router)
app.include_router(campaigns.router)
app.include_router(dashboard.router)
app.include_router(capture.router)
app.include_router(marketplace.router)


# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back or handle client messages
            await ws_manager.send_personal(websocket, {"event": "ack", "data": data})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
