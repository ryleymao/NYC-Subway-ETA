"""
Unit tests for health endpoint
"""
import pytest
from unittest.mock import Mock

from app.routers.health import health_check


@pytest.mark.asyncio
async def test_health_check_healthy(db_session, mock_redis):
    """Test health check when everything is healthy"""
    # Mock Redis health check
    mock_redis.ping.return_value = True
    mock_redis.info.return_value = {
        'connected_clients': 2,
        'used_memory_human': '2M'
    }

    response = await health_check(db_session)

    assert response.status == "healthy"
    assert response.db_ms is not None
    assert response.db_ms > 0
    assert response.redis_status["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_db_error(mock_redis):
    """Test health check when database is down"""
    # Mock a failing database session
    mock_db = Mock()
    mock_db.execute.side_effect = Exception("Database connection failed")

    response = await health_check(mock_db)

    assert response.status == "unhealthy"
    assert response.db_ms is None