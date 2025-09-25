from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ..state.store import ArrivalStore
from .schemas import ArrivalsResponse, RouteResponse, RouteLeg

router = APIRouter()

@router.get("/arrivals", response_model=ArrivalsResponse)
async def arrivals(stop_id: str, limit: int = Query(3, ge=1, le=10)):
    store = ArrivalStore()
    items = await store.get_arrivals(stop_id, limit=limit)
    return ArrivalsResponse(stop_id=stop_id, limit=limit, arrivals=items)

@router.get("/route", response_model=RouteResponse)
async def route(from_: str = Query(..., alias="from"), to: str = Query(..., alias="to")):
    # Stubbed path: replace with graph search + live headways
    legs = [
        RouteLeg(from_stop=from_, to_stop=to, route_id="N", travel_seconds=900, is_transfer=False)
    ]
    return RouteResponse(from_stop=from_, to_stop=to, eta_seconds=sum(l.travel_seconds for l in legs), legs=legs)
