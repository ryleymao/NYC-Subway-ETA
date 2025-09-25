from pydantic import BaseModel, Field
from typing import List, Optional

class Arrival(BaseModel):
    route_id: str
    trip_id: str
    stop_id: str
    headsign: str
    arrival_epoch: int  # unix seconds
    scheduled_epoch: Optional[int] = None
    is_approaching: bool = False

class ArrivalsResponse(BaseModel):
    stop_id: str
    limit: int = 3
    arrivals: List[Arrival] = Field(default_factory=list)

class RouteLeg(BaseModel):
    from_stop: str
    to_stop: str
    route_id: str
    travel_seconds: int
    is_transfer: bool = False

class RouteResponse(BaseModel):
    from_stop: str
    to_stop: str
    eta_seconds: int
    legs: List[RouteLeg]
