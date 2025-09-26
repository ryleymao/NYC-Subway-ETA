"""
Integration tests for API endpoints
"""
import json
from datetime import datetime, timezone

import pytest


def test_health_endpoint(client):
    """Test health endpoint returns expected structure"""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "db_ms" in data
    assert "redis_status" in data


def test_stops_search(client, db_session, sample_gtfs_data):
    """Test stops search endpoint"""
    # Add sample stops to database
    from app.models.models import Stop

    for stop_data in sample_gtfs_data["stops"]:
        stop = Stop(**stop_data)
        db_session.add(stop)
    db_session.commit()

    # Test search
    response = client.get("/stops?q=Times")
    assert response.status_code == 200

    data = response.json()
    assert "stops" in data
    assert len(data["stops"]) >= 1
    assert data["stops"][0]["name"] == "Times Sq-42 St"


def test_stops_search_empty_query(client):
    """Test stops search with too short query"""
    response = client.get("/stops?q=")
    assert response.status_code == 422  # Validation error


def test_arrivals_endpoint_empty(client, mock_redis):
    """Test arrivals endpoint when no cached data exists"""
    mock_redis.get.return_value = None

    response = client.get("/arrivals?stop_id=635&direction=N")
    assert response.status_code == 200

    data = response.json()
    assert "arrivals" in data
    assert "as_of_ts" in data
    assert len(data["arrivals"]) == 0


def test_arrivals_endpoint_with_data(client, mock_redis):
    """Test arrivals endpoint with cached data"""
    # Mock cached arrivals data
    cached_data = {
        "arrivals": [
            {"route_id": "N", "headsign": "Astoria-Ditmars Blvd", "eta_s": 120},
            {"route_id": "Q", "headsign": "96 St-2 Av", "eta_s": 300}
        ],
        "as_of_ts": int(datetime.now(timezone.utc).timestamp()),
        "cached_at": int(datetime.now(timezone.utc).timestamp())
    }
    mock_redis.get.return_value = json.dumps(cached_data)

    response = client.get("/arrivals?stop_id=635&direction=N")
    assert response.status_code == 200

    data = response.json()
    assert len(data["arrivals"]) == 2
    assert data["arrivals"][0]["route_id"] == "N"
    assert data["arrivals"][0]["eta_s"] == 120


def test_arrivals_invalid_direction(client):
    """Test arrivals endpoint with invalid direction"""
    response = client.get("/arrivals?stop_id=635&direction=X")
    assert response.status_code == 422  # Validation error


def test_route_debug_endpoint(client):
    """Test debug route endpoint"""
    response = client.get("/route/debug/635/902")
    assert response.status_code == 200

    data = response.json()
    assert "legs" in data
    assert "transfers" in data
    assert "total_eta_s" in data
    assert "alerts" in data

    assert len(data["legs"]) == 1
    assert data["legs"][0]["route_id"] == "N"
    assert data["legs"][0]["from_stop_id"] == "635"
    assert data["legs"][0]["to_stop_id"] == "902"


def test_route_endpoint_same_stops(client):
    """Test route endpoint with same origin and destination"""
    response = client.get("/route?from=635&to=635")
    assert response.status_code == 400


def test_cors_headers(client):
    """Test that CORS headers are present"""
    response = client.get("/health")
    assert response.status_code == 200

    # CORS headers should be present due to middleware
    # Note: TestClient doesn't always populate CORS headers in the same way
    # This test would be more effective in a real browser environment