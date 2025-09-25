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

# --- DEBUG SEED (for memory backend) ---
import time
from ..service.schemas import Arrival

@router.post("/debug/seed")
async def debug_seed():
    """
    Seeds arrivals for two demo stops (R23N, R23S) *inside* the API process.
    This is only for local dev when STORE_BACKEND=memory.
    """
    store = ArrivalStore()
    now = int(time.time())

    def mk(route, trip, stop, in_sec):
        return Arrival(
            route_id=route,
            trip_id=f"{trip}-{stop}",
            stop_id=stop,
            headsign=f"{route} to Downtown",
            arrival_epoch=now + in_sec,
            scheduled_epoch=None,
            is_approaching=in_sec < 120,
        )

    for stop in ("R23N", "R23S"):
        arrs = [
            mk("N", "trip1", stop, 90),
            mk("N", "trip2", stop, 240),
            mk("R", "trip3", stop, 420),
        ]
        await store.put_arrivals(stop, arrs)

    return {"ok": True, "seeded": ["R23N", "R23S"], "count_per_stop": 3}
