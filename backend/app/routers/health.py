"""
Health check endpoint
"""
import time
import logging
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.core.cache import arrivals_cache
from app.models.dto import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint
    Returns service status, feed age, and database response time
    """
    try:
        # Test database connectivity and measure response time
        start_time = time.time()
        db.execute(text("SELECT 1"))
        db_response_time_ms = (time.time() - start_time) * 1000

        # Get Redis status and feed age
        redis_status = arrivals_cache.health_check()
        feed_age_seconds = arrivals_cache.get_feed_age()

        return HealthResponse(
            status="healthy",
            feed_age_seconds=feed_age_seconds,
            db_ms=round(db_response_time_ms, 2),
            redis_status=redis_status
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            feed_age_seconds=None,
            db_ms=None,
            redis_status={"status": "error", "error": str(e)}
        )