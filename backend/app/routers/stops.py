"""
Stops search endpoint for station autocomplete
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.core.database import get_db
from app.models.models import Stop, Route, Trip, StopTime
from app.models.dto import StopsResponse, StopInfo

logger = logging.getLogger(__name__)

router = APIRouter()


def get_lines_for_stop(db: Session, stop_id: str) -> List[str]:
    """Get all route/line IDs that serve a stop"""
    try:
        # TODO: This is a simplified implementation
        # In production, you'd want to cache this and handle NYC-specific logic
        # for grouping express/local services, handling complex IDs, etc.

        lines = db.query(Route.route_short_name).distinct().join(
            Trip, Trip.route_id == Route.route_id
        ).join(
            StopTime, StopTime.trip_id == Trip.trip_id
        ).filter(
            StopTime.stop_id == stop_id,
            Route.route_short_name.isnot(None)
        ).all()

        return [line[0] for line in lines if line[0]]

    except Exception as e:
        logger.error(f"Error getting lines for stop {stop_id}: {e}")
        return []


@router.get("/stops", response_model=StopsResponse)
async def search_stops(
    q: str = Query(..., min_length=1, description="Search query"),
    db: Session = Depends(get_db)
):
    """
    Station autocomplete search
    Returns stations matching the query with their served lines
    Special query '*' returns all stations (for map loading)
    """
    try:
        # Special case: return all stations for map loading
        if q == "*":
            query = db.query(Stop).filter(
                Stop.location_type == 0
            ).limit(1000)  # Show all stations for map display
        else:
            # Normal search
            query = db.query(Stop).filter(
                or_(
                    Stop.stop_name.ilike(f"%{q}%"),
                    Stop.stop_id.ilike(f"%{q}%")
                ),
                # Only return actual stops, not parent stations
                Stop.location_type == 0
            ).limit(20)

        stops = query.all()

        # Build response
        stop_infos = []
        for stop in stops:
            lines = get_lines_for_stop(db, stop.stop_id)
            stop_infos.append(StopInfo(
                id=stop.stop_id,
                name=stop.stop_name,
                lines=lines,
                lat=float(stop.stop_lat) if stop.stop_lat else None,
                lon=float(stop.stop_lon) if stop.stop_lon else None
            ))

        return StopsResponse(stops=stop_infos)

    except Exception as e:
        logger.error(f"Error searching stops with query '{q}': {e}")
        raise HTTPException(status_code=500, detail="Failed to search stops")