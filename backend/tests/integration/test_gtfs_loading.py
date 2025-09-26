"""
Integration tests for GTFS static data loading
"""
import pytest
from pathlib import Path

from app.core.gtfs_static import GTFSStaticLoader
from app.models.models import Agency, Route, Stop


def test_gtfs_loader_agencies(db_session, temp_gtfs_dir):
    """Test loading agencies from GTFS data"""
    loader = GTFSStaticLoader(str(temp_gtfs_dir))
    agency_file = temp_gtfs_dir / "agency.txt"

    count = loader._load_agencies(db_session, agency_file)
    assert count == 1

    # Verify data was loaded
    agency = db_session.query(Agency).first()
    assert agency is not None
    assert agency.agency_id == "MTA"
    assert agency.agency_name == "Metropolitan Transportation Authority"


def test_gtfs_loader_routes(db_session, temp_gtfs_dir):
    """Test loading routes from GTFS data"""
    loader = GTFSStaticLoader(str(temp_gtfs_dir))
    routes_file = temp_gtfs_dir / "routes.txt"

    count = loader._load_routes(db_session, routes_file)
    assert count == 1

    # Verify data was loaded
    route = db_session.query(Route).first()
    assert route is not None
    assert route.route_id == "N"
    assert route.route_short_name == "N"


def test_gtfs_loader_stops(db_session, temp_gtfs_dir):
    """Test loading stops from GTFS data"""
    loader = GTFSStaticLoader(str(temp_gtfs_dir))
    stops_file = temp_gtfs_dir / "stops.txt"

    count = loader._load_stops(db_session, stops_file)
    assert count == 2

    # Verify data was loaded
    stops = db_session.query(Stop).all()
    assert len(stops) == 2

    times_sq = next(s for s in stops if s.stop_id == "635")
    assert times_sq.stop_name == "Times Sq-42 St"
    assert abs(times_sq.stop_lat - 40.754672) < 0.0001


def test_gtfs_time_parsing():
    """Test GTFS time string parsing"""
    from app.core.gtfs_static import GTFSStaticLoader

    loader = GTFSStaticLoader("dummy")

    # Test normal time
    assert loader._parse_gtfs_time("08:30:45") == 8 * 3600 + 30 * 60 + 45

    # Test time after midnight (next day service)
    assert loader._parse_gtfs_time("25:15:30") == 25 * 3600 + 15 * 60 + 30

    # Test empty string
    assert loader._parse_gtfs_time("") == 0