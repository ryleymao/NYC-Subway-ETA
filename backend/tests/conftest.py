"""
Pytest configuration and fixtures
"""
import pytest
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import Mock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db, Base
from app.core.cache import get_redis
from app.core.config import get_settings


@pytest.fixture(scope="session")
def test_db_engine():
    """Create test database engine using SQLite"""
    engine = create_engine(
        "sqlite:///./test.db",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_db_engine) -> Generator[Session, None, None]:
    """Create a test database session"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def mock_redis():
    """Mock Redis client for tests"""
    mock_redis = Mock()
    mock_redis.get.return_value = None
    mock_redis.setex.return_value = True
    mock_redis.set.return_value = True
    mock_redis.ping.return_value = True
    mock_redis.keys.return_value = []
    mock_redis.info.return_value = {
        'connected_clients': 1,
        'used_memory_human': '1M'
    }
    return mock_redis


@pytest.fixture
def client(db_session, mock_redis):
    """Create test client with overridden dependencies"""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_redis():
        return mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def sample_gtfs_data():
    """Create sample GTFS static data for tests"""
    return {
        "agencies": [
            {
                "agency_id": "MTA",
                "agency_name": "Metropolitan Transportation Authority",
                "agency_url": "https://mta.info",
                "agency_timezone": "America/New_York"
            }
        ],
        "routes": [
            {
                "route_id": "N",
                "agency_id": "MTA",
                "route_short_name": "N",
                "route_long_name": "Broadway Express",
                "route_type": 1,
                "route_color": "FCCC0A"
            },
            {
                "route_id": "Q",
                "agency_id": "MTA",
                "route_short_name": "Q",
                "route_long_name": "Broadway Express",
                "route_type": 1,
                "route_color": "FCCC0A"
            }
        ],
        "stops": [
            {
                "stop_id": "635",
                "stop_name": "Times Sq-42 St",
                "stop_lat": 40.754672,
                "stop_lon": -73.986754,
                "location_type": 0
            },
            {
                "stop_id": "902",
                "stop_name": "Herald Sq-34 St",
                "stop_lat": 40.749567,
                "stop_lon": -73.987691,
                "location_type": 0
            }
        ],
        "trips": [
            {
                "trip_id": "N_trip_1",
                "route_id": "N",
                "service_id": "weekday",
                "trip_headsign": "Astoria-Ditmars Blvd",
                "direction_id": 0
            }
        ],
        "stop_times": [
            {
                "trip_id": "N_trip_1",
                "stop_id": "635",
                "stop_sequence": 1,
                "arrival_time": "08:00:00",
                "departure_time": "08:00:30"
            },
            {
                "trip_id": "N_trip_1",
                "stop_id": "902",
                "stop_sequence": 2,
                "arrival_time": "08:03:00",
                "departure_time": "08:03:30"
            }
        ]
    }


@pytest.fixture
def sample_gtfs_rt_data():
    """Sample GTFS-RT protobuf data (as dict for easy testing)"""
    return {
        "header": {
            "gtfs_realtime_version": "2.0",
            "timestamp": 1640995200
        },
        "entity": [
            {
                "id": "N_trip_1_update",
                "trip_update": {
                    "trip": {
                        "trip_id": "N_trip_1",
                        "route_id": "N"
                    },
                    "stop_time_update": [
                        {
                            "stop_id": "635N",
                            "arrival": {
                                "time": 1640995320  # 2 minutes from now
                            }
                        },
                        {
                            "stop_id": "902N",
                            "arrival": {
                                "time": 1640995500  # 5 minutes from now
                            }
                        }
                    ]
                }
            }
        ]
    }


@pytest.fixture
def temp_gtfs_dir():
    """Create temporary directory with sample GTFS files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        gtfs_path = Path(temp_dir)

        # Create agency.txt
        agency_data = "agency_id,agency_name,agency_url,agency_timezone\nMTA,Metropolitan Transportation Authority,https://mta.info,America/New_York\n"
        (gtfs_path / "agency.txt").write_text(agency_data)

        # Create routes.txt
        routes_data = "route_id,agency_id,route_short_name,route_long_name,route_type,route_color\nN,MTA,N,Broadway Express,1,FCCC0A\n"
        (gtfs_path / "routes.txt").write_text(routes_data)

        # Create stops.txt
        stops_data = "stop_id,stop_name,stop_lat,stop_lon,location_type\n635,Times Sq-42 St,40.754672,-73.986754,0\n902,Herald Sq-34 St,40.749567,-73.987691,0\n"
        (gtfs_path / "stops.txt").write_text(stops_data)

        yield gtfs_path