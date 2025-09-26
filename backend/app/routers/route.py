"""
Transfer-aware routing endpoint
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.routing import route_planner
from app.models.dto import RouteResponse, RouteLeg, AlertInfo

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/route", response_model=RouteResponse)
async def plan_route(
    from_stop_id: str = Query(..., alias="from", description="Origin stop ID"),
    to_stop_id: str = Query(..., alias="to", description="Destination stop ID"),
    db: Session = Depends(get_db)
):
    """
    Plan the best route from origin to destination with transfer-aware routing
    Uses pre-computed station graph + Dijkstra algorithm with live first-leg overlay
    """
    try:
        if from_stop_id == to_stop_id:
            raise HTTPException(status_code=400, detail="Origin and destination cannot be the same")

        # TODO: Validate that both stops exist in the database
        # TODO: Use the routing engine to find the best path

        # Placeholder implementation - replace with actual routing logic
        route_result = await route_planner.find_best_route(
            from_stop_id=from_stop_id,
            to_stop_id=to_stop_id,
            db=db
        )

        if not route_result:
            raise HTTPException(
                status_code=404,
                detail=f"No route found between {from_stop_id} and {to_stop_id}"
            )

        return route_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error planning route from {from_stop_id} to {to_stop_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to plan route")


@router.get("/route/debug/{from_stop_id}/{to_stop_id}", response_model=RouteResponse)
async def debug_route(
    from_stop_id: str,
    to_stop_id: str,
    db: Session = Depends(get_db)
):
    """
    Debug endpoint that returns a mock route for testing
    """
    try:
        # Mock response for testing purposes
        mock_legs = [
            RouteLeg(
                route_id="N",
                from_stop_id=from_stop_id,
                to_stop_id=to_stop_id,
                board_in_s=120,  # 2 minutes to board
                run_s=480,       # 8 minutes travel time
                transfer=False
            )
        ]

        return RouteResponse(
            legs=mock_legs,
            transfers=0,
            total_eta_s=600,  # 10 minutes total
            alerts=[]
        )

    except Exception as e:
        logger.error(f"Error in debug route: {e}")
        raise HTTPException(status_code=500, detail="Debug route failed")