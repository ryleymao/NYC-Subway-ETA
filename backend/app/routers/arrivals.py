"""
Real-time arrivals endpoint
"""
import logging
from typing import List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, HTTPException

from app.core.cache import arrivals_cache
from app.models.dto import ArrivalsResponse, Arrival, Direction

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/arrivals", response_model=ArrivalsResponse)
async def get_arrivals(
    stop_id: str = Query(..., description="Stop ID"),
    direction: Direction = Query(..., description="Direction (N/S/E/W)")
):
    """
    Get real-time arrivals for a stop in a specific direction
    Returns live ETA data from Redis cache populated by GTFS-RT background fetcher
    """
    try:
        # Get arrivals from Redis cache
        arrivals = arrivals_cache.get_arrivals(stop_id, direction.value)

        if arrivals is None:
            # No cached data available
            logger.warning(f"No arrivals data for stop {stop_id} direction {direction.value}")
            arrivals = []

        # TODO: Filter out arrivals that are too old (> 30-60 minutes)
        # TODO: Sort by ETA
        arrivals = sorted(arrivals, key=lambda a: a.eta_s)

        # Get timestamp for when this data was last updated
        current_timestamp = int(datetime.now(timezone.utc).timestamp())

        return ArrivalsResponse(
            arrivals=arrivals,
            as_of_ts=current_timestamp
        )

    except Exception as e:
        logger.error(f"Error getting arrivals for stop {stop_id} direction {direction.value}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get arrivals data")


@router.get("/arrivals/{stop_id}", response_model=ArrivalsResponse)
async def get_arrivals_all_directions(stop_id: str):
    """
    Get arrivals for all directions at a stop (convenience endpoint)
    """
    try:
        all_arrivals = []

        # Try all four directions
        for direction in [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]:
            arrivals = arrivals_cache.get_arrivals(stop_id, direction.value)
            if arrivals:
                all_arrivals.extend(arrivals)

        # Sort by ETA
        all_arrivals = sorted(all_arrivals, key=lambda a: a.eta_s)

        current_timestamp = int(datetime.now(timezone.utc).timestamp())

        return ArrivalsResponse(
            arrivals=all_arrivals,
            as_of_ts=current_timestamp
        )

    except Exception as e:
        logger.error(f"Error getting all arrivals for stop {stop_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get arrivals data")