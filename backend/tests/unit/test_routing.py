"""
Unit tests for routing algorithms
"""
from collections import defaultdict

import pytest

from app.core.routing import RoutePlanner


def test_dijkstra_simple_path():
    """Test Dijkstra algorithm with simple path"""
    planner = RoutePlanner()

    # Create simple graph: A -> B -> C
    planner.graph = {
        "A": {
            "B": [{"route_id": "1", "travel_time": 300, "is_transfer": False, "transfer_penalty": 0}]
        },
        "B": {
            "C": [{"route_id": "1", "travel_time": 240, "is_transfer": False, "transfer_penalty": 0}]
        }
    }

    path = planner._dijkstra("A", "C", max_transfers=2)

    assert path is not None
    assert len(path) == 2
    assert path[0] == ("A", "B", "1", 300, False)
    assert path[1] == ("B", "C", "1", 240, False)


def test_dijkstra_with_transfer():
    """Test Dijkstra algorithm with transfer"""
    planner = RoutePlanner()

    # Create graph with transfer: A -> B (route 1), transfer B -> B, B -> C (route 2)
    planner.graph = {
        "A": {
            "B": [{"route_id": "1", "travel_time": 300, "is_transfer": False, "transfer_penalty": 0}]
        },
        "B": {
            "B": [{"route_id": "TRANSFER", "travel_time": 0, "is_transfer": True, "transfer_penalty": 180}],
            "C": [{"route_id": "2", "travel_time": 240, "is_transfer": False, "transfer_penalty": 0}]
        }
    }

    path = planner._dijkstra("A", "C", max_transfers=2)

    assert path is not None
    assert len(path) == 3
    assert path[0][4] is False  # First leg not a transfer
    assert path[1][4] is True   # Transfer
    assert path[2][4] is False  # Second leg not a transfer


def test_dijkstra_no_path():
    """Test Dijkstra when no path exists"""
    planner = RoutePlanner()

    # Create disconnected graph
    planner.graph = {
        "A": {
            "B": [{"route_id": "1", "travel_time": 300, "is_transfer": False, "transfer_penalty": 0}]
        },
        "C": {
            "D": [{"route_id": "2", "travel_time": 240, "is_transfer": False, "transfer_penalty": 0}]
        }
    }

    path = planner._dijkstra("A", "D", max_transfers=2)
    assert path is None


def test_dijkstra_max_transfers_limit():
    """Test that max transfers limit is respected"""
    planner = RoutePlanner()

    # Create graph requiring 3 transfers
    planner.graph = {
        "A": {
            "B": [{"route_id": "TRANSFER", "travel_time": 0, "is_transfer": True, "transfer_penalty": 180}]
        },
        "B": {
            "C": [{"route_id": "TRANSFER", "travel_time": 0, "is_transfer": True, "transfer_penalty": 180}]
        },
        "C": {
            "D": [{"route_id": "TRANSFER", "travel_time": 0, "is_transfer": True, "transfer_penalty": 180}]
        },
        "D": {
            "E": [{"route_id": "1", "travel_time": 300, "is_transfer": False, "transfer_penalty": 0}]
        }
    }

    # Should find path with max_transfers=3
    path = planner._dijkstra("A", "E", max_transfers=3)
    assert path is not None

    # Should not find path with max_transfers=2
    path = planner._dijkstra("A", "E", max_transfers=2)
    assert path is None


def test_path_to_legs_simple():
    """Test converting path to route legs"""
    planner = RoutePlanner()

    # Simple path without transfers
    path = [
        ("A", "B", "N", 300, False),
        ("B", "C", "N", 240, False)
    ]

    # Mock the live boarding time function to return None (use scheduled)
    async def mock_get_live_boarding_time(stop_id, route_id):
        return None

    planner._get_live_boarding_time = mock_get_live_boarding_time

    # Test conversion
    import asyncio
    legs = asyncio.run(planner._path_to_legs(path, None))

    assert len(legs) == 2
    assert legs[0].route_id == "N"
    assert legs[0].from_stop_id == "A"
    assert legs[0].to_stop_id == "B"
    assert legs[0].board_in_s == 300
    assert legs[0].run_s == 300
    assert legs[0].transfer is False

    assert legs[1].route_id == "N"
    assert legs[1].from_stop_id == "B"
    assert legs[1].to_stop_id == "C"
    assert legs[1].run_s == 240
    assert legs[1].transfer is True  # Second leg is a transfer


def test_path_to_legs_with_transfers():
    """Test converting path with transfer edges to legs"""
    planner = RoutePlanner()

    # Path with transfer edge
    path = [
        ("A", "B", "N", 300, False),
        ("B", "B", "TRANSFER", 0, True),
        ("B", "C", "Q", 240, False)
    ]

    # Mock the live boarding time function
    async def mock_get_live_boarding_time(stop_id, route_id):
        return None

    planner._get_live_boarding_time = mock_get_live_boarding_time

    # Test conversion - transfer edges should be skipped
    import asyncio
    legs = asyncio.run(planner._path_to_legs(path, None))

    assert len(legs) == 2  # Transfer edge should be skipped
    assert legs[0].route_id == "N"
    assert legs[1].route_id == "Q"
    assert legs[1].transfer is True