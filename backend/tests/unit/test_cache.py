"""
Unit tests for Redis cache functionality
"""
import json
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from app.core.cache import ArrivalsCache
from app.models.dto import Arrival


def test_arrivals_cache_get_empty():
    """Test getting arrivals when cache is empty"""
    mock_redis = Mock()
    mock_redis.get.return_value = None

    cache = ArrivalsCache()
    cache.redis = mock_redis

    result = cache.get_arrivals("635", "N")
    assert result is None


def test_arrivals_cache_set_and_get():
    """Test setting and getting arrivals from cache"""
    mock_redis = Mock()
    cache = ArrivalsCache()
    cache.redis = mock_redis

    # Test data
    arrivals = [
        Arrival(route_id="N", headsign="Astoria-Ditmars Blvd", eta_s=120),
        Arrival(route_id="Q", headsign="96 St-2 Av", eta_s=300)
    ]

    # Mock successful set
    mock_redis.setex.return_value = True

    # Test setting arrivals
    result = cache.set_arrivals("635", "N", arrivals)
    assert result is True

    # Verify setex was called with correct parameters
    mock_redis.setex.assert_called_once()
    call_args = mock_redis.setex.call_args
    assert call_args[0][0] == "arrivals:635:N"  # key
    assert call_args[0][1] == cache.ttl  # TTL

    # Parse the JSON data that was stored
    stored_data = json.loads(call_args[0][2])
    assert len(stored_data["arrivals"]) == 2
    assert stored_data["arrivals"][0]["route_id"] == "N"
    assert stored_data["arrivals"][0]["eta_s"] == 120


def test_arrivals_cache_get_existing():
    """Test getting existing arrivals from cache"""
    mock_redis = Mock()
    cache = ArrivalsCache()
    cache.redis = mock_redis

    # Mock cached data
    cached_data = {
        "arrivals": [
            {"route_id": "N", "headsign": "Astoria-Ditmars Blvd", "eta_s": 120},
            {"route_id": "Q", "headsign": "96 St-2 Av", "eta_s": 300}
        ],
        "as_of_ts": int(datetime.now(timezone.utc).timestamp()),
        "cached_at": int(datetime.now(timezone.utc).timestamp())
    }
    mock_redis.get.return_value = json.dumps(cached_data)

    # Test getting arrivals
    result = cache.get_arrivals("635", "N")

    assert result is not None
    assert len(result) == 2
    assert result[0].route_id == "N"
    assert result[0].eta_s == 120
    assert result[1].route_id == "Q"
    assert result[1].eta_s == 300


def test_feed_age():
    """Test feed age calculation"""
    mock_redis = Mock()
    cache = ArrivalsCache()
    cache.redis = mock_redis

    # Mock timestamp from 30 seconds ago
    past_timestamp = datetime.now(timezone.utc).timestamp() - 30
    mock_redis.get.return_value = str(past_timestamp)

    age = cache.get_feed_age()
    assert age is not None
    assert 29 <= age <= 31  # Should be around 30 seconds


def test_health_check():
    """Test Redis health check"""
    mock_redis = Mock()
    cache = ArrivalsCache()
    cache.redis = mock_redis

    # Mock healthy Redis
    mock_redis.ping.return_value = True
    mock_redis.info.return_value = {
        'connected_clients': 5,
        'used_memory_human': '10M'
    }
    mock_redis.keys.return_value = ['arrivals:635:N', 'arrivals:902:S']

    result = cache.health_check()

    assert result["status"] == "healthy"
    assert result["connected_clients"] == 5
    assert result["used_memory"] == "10M"
    assert result["cached_arrivals"] == 2