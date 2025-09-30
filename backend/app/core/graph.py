"""
Station graph building and management for routing
"""
import logging
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.models import Stop, StopTime, Trip, Route, Transfer, StationGraph
from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class StationGraphBuilder:
    """Builds a station graph from GTFS static data for routing"""

    def __init__(self):
        self.graph: Dict[str, Dict[str, List[Dict]]] = defaultdict(lambda: defaultdict(list))

    def build_graph(self, db: Session) -> Dict[str, int]:
        """
        Build station graph from GTFS static data
        Returns counts of edges created
        """
        logger.info("Building station graph...")

        counts = {
            "consecutive_stops": 0,
            "transfers": 0,
            "total_edges": 0
        }

        # 1. Build consecutive stop connections from GTFS data
        counts["consecutive_stops"] = self._build_consecutive_connections(db)

        # 2. Add transfer connections
        counts["transfers"] = self._build_transfer_connections(db)

        # 3. Store graph in database
        self._save_graph_to_db(db)

        counts["total_edges"] = counts["consecutive_stops"] + counts["transfers"]
        logger.info(f"Graph building complete: {counts}")

        return counts

    def _build_consecutive_connections(self, db: Session) -> int:
        """Build connections between consecutive stops on the same route"""
        logger.info("Building consecutive stop connections...")

        # Query to get consecutive stops with travel times
        query = text("""
            SELECT DISTINCT
                st1.stop_id as from_stop_id,
                st2.stop_id as to_stop_id,
                t.route_id,
                st1.departure_time,
                st2.arrival_time,
                st2.stop_sequence - st1.stop_sequence as sequence_diff
            FROM stop_times st1
            JOIN stop_times st2 ON (
                st1.trip_id = st2.trip_id
                AND st2.stop_sequence = st1.stop_sequence + 1
            )
            JOIN trips t ON st1.trip_id = t.trip_id
            WHERE st1.departure_time IS NOT NULL
            AND st2.arrival_time IS NOT NULL
            ORDER BY st1.stop_id, st2.stop_id, t.route_id
        """)

        result = db.execute(query)
        connections = defaultdict(list)

        for row in result:
            from_stop = row.from_stop_id
            to_stop = row.to_stop_id
            route_id = row.route_id

            # Calculate travel time (simplified - assumes same day)
            try:
                dep_time = self._parse_gtfs_time(row.departure_time)
                arr_time = self._parse_gtfs_time(row.arrival_time)
                travel_seconds = max(60, arr_time - dep_time)  # Minimum 1 minute
            except:
                travel_seconds = 120  # Default 2 minutes

            connections[(from_stop, to_stop, route_id)].append(travel_seconds)

        # Average travel times for same connections
        count = 0
        for (from_stop, to_stop, route_id), times in connections.items():
            avg_time = int(sum(times) / len(times))

            self.graph[from_stop][to_stop].append({
                'route_id': route_id,
                'travel_time': avg_time,
                'is_transfer': False,
                'transfer_penalty': 0
            })
            count += 1

        logger.info(f"Built {count} consecutive stop connections")
        return count

    def _build_transfer_connections(self, db: Session) -> int:
        """Build transfer connections between different routes/stations"""
        logger.info("Building transfer connections...")

        # 1. Load explicit transfers from GTFS transfers.txt
        explicit_transfers = db.query(Transfer).all()
        count = 0

        for transfer in explicit_transfers:
            # Skip same-stop transfers and impossible transfers
            if (transfer.from_stop_id == transfer.to_stop_id or
                transfer.transfer_type == 3):  # 3 = not possible
                continue

            # Calculate transfer time
            if transfer.min_transfer_time:
                transfer_time = transfer.min_transfer_time
            else:
                # Default transfer penalty based on type
                if transfer.transfer_type == 0:  # Recommended
                    transfer_time = settings.transfer_penalty_min
                elif transfer.transfer_type == 1:  # Timed
                    transfer_time = settings.transfer_penalty_min
                else:  # Minimum time required
                    transfer_time = settings.transfer_penalty_max

            # Create transfer connections for all directional combinations
            # since the routing algorithm uses directional stop IDs
            from_variations = self._get_directional_variations(transfer.from_stop_id)
            to_variations = self._get_directional_variations(transfer.to_stop_id)

            for from_dir in from_variations:
                for to_dir in to_variations:
                    self.graph[from_dir][to_dir].append({
                        'route_id': 'TRANSFER',
                        'travel_time': 0,
                        'is_transfer': True,
                        'transfer_penalty': transfer_time
                    })
                    count += 1

        # 2. Add intra-station transfers (platform-to-platform within same station)
        intra_station_count = self._build_intra_station_transfers(db)
        count += intra_station_count
        logger.info(f"Built {intra_station_count} intra-station transfers")

        # 3. TODO: Add implicit transfers between nearby stops
        # This would involve finding stops within walking distance
        # and creating transfer connections between them

        logger.info(f"Built {count} transfer connections")
        return count

    def _build_intra_station_transfers(self, db: Session) -> int:
        """Build transfers between different platforms at the same station"""
        logger.info("Building intra-station transfers (platform-to-platform)...")

        # Get all unique base station IDs
        from app.models.models import Stop
        base_stations = db.query(Stop.stop_id).distinct().all()
        count = 0

        for (base_id,) in base_stations:
            # Find all directional platforms for this station
            platforms = []
            for direction in ['N', 'S', 'E', 'W']:
                platform_id = f"{base_id}{direction}"
                if platform_id in self.graph:
                    platforms.append(platform_id)

            # Only create transfers if there are actual routes serving different platforms
            # This prevents unnecessary platform transfers when direct routes exist
            if len(platforms) > 1:
                for i, from_platform in enumerate(platforms):
                    for j, to_platform in enumerate(platforms):
                        if i != j:  # Don't transfer to yourself
                            # Platform-to-platform transfer (e.g., 106N -> 106S)
                            # Increase penalty to discourage unless necessary
                            self.graph[from_platform][to_platform].append({
                                'route_id': 'PLATFORM_TRANSFER',
                                'travel_time': 0,
                                'is_transfer': True,
                                'transfer_penalty': 300  # 5 minutes to discourage platform transfers
                            })
                            count += 1

        logger.info(f"Built {count} intra-station platform transfers")
        return count

    def _save_graph_to_db(self, db: Session):
        """Save the computed graph to the database for fast routing queries"""
        logger.info("Saving graph to database...")

        # Clear existing graph
        db.execute(text("DELETE FROM station_graph"))

        # Insert new graph edges
        edges = []
        for from_stop, destinations in self.graph.items():
            for to_stop, connections in destinations.items():
                for conn in connections:
                    edges.append(StationGraph(
                        from_stop_id=from_stop,
                        to_stop_id=to_stop,
                        route_id=conn['route_id'],
                        travel_time_seconds=conn['travel_time'],
                        is_transfer=conn['is_transfer'],
                        transfer_penalty_seconds=conn['transfer_penalty']
                    ))

        # Insert in batches
        batch_size = 1000
        for i in range(0, len(edges), batch_size):
            batch = edges[i:i + batch_size]
            db.add_all(batch)
            db.flush()

        db.commit()
        logger.info(f"Saved {len(edges)} graph edges to database")

    def _get_directional_variations(self, base_stop_id: str) -> List[str]:
        """Get all directional variations of a stop ID that exist in the graph"""
        # If the stop ID already has a direction, return it
        if base_stop_id.endswith(('N', 'S', 'E', 'W')):
            return [base_stop_id]

        # Try all possible directions and return those that exist in the graph
        possible_ids = [
            f"{base_stop_id}N",
            f"{base_stop_id}S",
            f"{base_stop_id}E",
            f"{base_stop_id}W"
        ]

        # Return all variations - we'll filter later when the graph is complete
        return [stop_id for stop_id in possible_ids]

    def _parse_gtfs_time(self, time_str: str) -> int:
        """
        Parse GTFS time string (HH:MM:SS) to seconds since midnight
        Handles times > 24:00:00 for next day service
        """
        if not time_str:
            return 0

        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])

        return hours * 3600 + minutes * 60 + seconds

    def get_graph(self) -> Dict[str, Dict[str, List[Dict]]]:
        """Get the current graph"""
        return dict(self.graph)


def load_graph_from_db(db: Session) -> Dict[str, Dict[str, List[Dict]]]:
    """Load pre-computed graph from database"""
    graph = defaultdict(lambda: defaultdict(list))

    edges = db.query(StationGraph).all()

    for edge in edges:
        graph[edge.from_stop_id][edge.to_stop_id].append({
            'route_id': edge.route_id,
            'travel_time': edge.travel_time_seconds,
            'is_transfer': edge.is_transfer,
            'transfer_penalty': edge.transfer_penalty_seconds
        })

    return dict(graph)


# Global graph builder instance
graph_builder = StationGraphBuilder()