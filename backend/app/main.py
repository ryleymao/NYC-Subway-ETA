"""
NYC Subway ETA + Transfer-Aware Routing Service
FastAPI main application module
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import health, stops, arrivals, route as route_router
from app.core.config import get_settings
from app.core.database import engine
from app.core.cache import get_redis
from app.models import models

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager"""
    settings = get_settings()
    logger.info(f"Starting NYC Subway ETA service on {settings.environment}")

    # TODO: Initialize database tables
    # TODO: Start background GTFS-RT fetcher
    # TODO: Load GTFS static data if needed

    yield

    # Cleanup
    logger.info("Shutting down NYC Subway ETA service")


app = FastAPI(
    title="NYC Subway ETA API",
    description="Real-time NYC Subway ETA + transfer-aware routing service using MTA GTFS static + GTFS-Realtime",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="", tags=["health"])
app.include_router(stops.router, prefix="", tags=["stops"])
app.include_router(arrivals.router, prefix="", tags=["arrivals"])
app.include_router(route_router.router, prefix="", tags=["routing"])