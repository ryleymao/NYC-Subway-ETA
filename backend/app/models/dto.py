"""
Pydantic DTOs for API requests and responses
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Direction(str, Enum):
    """Cardinal directions for subway lines"""
    NORTH = "N"
    SOUTH = "S"
    EAST = "E"
    WEST = "W"


class HealthResponse(BaseModel):
    """Health endpoint response"""
    status: str
    feed_age_seconds: Optional[int] = None
    db_ms: Optional[float] = None
    redis_status: Optional[Dict[str, Any]] = None


class StopInfo(BaseModel):
    """Stop information for autocomplete"""
    id: str
    name: str
    lines: List[str]
    lat: Optional[float] = None
    lon: Optional[float] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "635",
                "name": "Times Sq-42 St",
                "lines": ["N", "Q", "R", "W", "S", "1", "2", "3", "7"]
            }
        }


class StopsResponse(BaseModel):
    """Response for stops search endpoint"""
    stops: List[StopInfo]


class Arrival(BaseModel):
    """Single arrival prediction"""
    route_id: str
    headsign: str
    eta_s: int = Field(..., description="Arrival time in seconds from now")

    class Config:
        json_schema_extra = {
            "example": {
                "route_id": "N",
                "headsign": "Astoria-Ditmars Blvd",
                "eta_s": 120
            }
        }


class ArrivalsResponse(BaseModel):
    """Response for arrivals endpoint"""
    arrivals: List[Arrival]
    as_of_ts: int = Field(..., description="Unix timestamp of data")

    class Config:
        json_schema_extra = {
            "example": {
                "arrivals": [
                    {"route_id": "N", "headsign": "Astoria-Ditmars Blvd", "eta_s": 120},
                    {"route_id": "Q", "headsign": "96 St-2 Av", "eta_s": 300}
                ],
                "as_of_ts": 1640995200
            }
        }


class RouteLeg(BaseModel):
    """Single leg of a route"""
    route_id: str
    from_stop_id: str
    to_stop_id: str
    from_stop_name: str = Field(..., description="Origin station name")
    to_stop_name: str = Field(..., description="Destination station name")
    board_in_s: int = Field(..., description="Time to board in seconds")
    run_s: int = Field(..., description="Travel time in seconds")
    transfer: bool = Field(False, description="Whether this is a transfer leg")
    direction: Optional[str] = Field(None, description="Travel direction (Uptown/Downtown/etc)")
    line_color: Optional[str] = Field(None, description="Subway line color")
    instruction: str = Field(..., description="Human-readable instruction")

    class Config:
        json_schema_extra = {
            "example": {
                "route_id": "N",
                "from_stop_id": "635",
                "to_stop_id": "902",
                "from_stop_name": "14 St-Union Sq",
                "to_stop_name": "Times Sq-42 St",
                "board_in_s": 120,
                "run_s": 480,
                "transfer": False,
                "direction": "Uptown",
                "line_color": "#FCCC0A",
                "instruction": "Take N train uptown to Times Sq-42 St (8 min ride, next train in 2 min)"
            }
        }


class AlertInfo(BaseModel):
    """Alert information"""
    id: str
    header: str


class RouteResponse(BaseModel):
    """Response for route planning endpoint"""
    legs: List[RouteLeg]
    transfers: int = Field(..., description="Number of transfers required")
    total_eta_s: int = Field(..., description="Total travel time in seconds")
    alerts: List[AlertInfo] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "legs": [
                    {
                        "route_id": "N",
                        "from_stop_id": "635",
                        "to_stop_id": "902",
                        "board_in_s": 120,
                        "run_s": 480,
                        "transfer": False
                    }
                ],
                "transfers": 0,
                "total_eta_s": 600,
                "alerts": []
            }
        }


# Request models
class StopsRequest(BaseModel):
    """Query parameters for stops endpoint"""
    q: str = Field(..., min_length=1, description="Search query")


class ArrivalsRequest(BaseModel):
    """Query parameters for arrivals endpoint"""
    stop_id: str = Field(..., description="Stop ID")
    direction: Direction = Field(..., description="Direction (N/S/E/W)")


class RouteRequest(BaseModel):
    """Query parameters for route endpoint"""
    from_stop_id: str = Field(..., description="Origin stop ID")
    to_stop_id: str = Field(..., description="Destination stop ID")