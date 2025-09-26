"""
Transfer-aware routing engine using Dijkstra's algorithm
"""
import heapq
import logging
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timezone
from collections import defaultdict

from sqlalchemy.orm import Session

from app.core.graph import load_graph_from_db
from app.core.cache import arrivals_cache
from app.core.config import get_settings
from app.models.dto import RouteResponse, RouteLeg, AlertInfo, Arrival

logger = logging.getLogger(__name__)

settings = get_settings()


class RoutePlanner:
    """Transfer-aware route planning using Dijkstra's algorithm"""

    def __init__(self):
        self.graph: Dict[str, Dict[str, List[Dict]]] = {}
        self.graph_loaded = False

    def _ensure_graph_loaded(self, db: Session):
        """Load graph from database if not already loaded"""
        if not self.graph_loaded:
            logger.info("Loading station graph from database...")
            self.graph = load_graph_from_db(db)
            self.graph_loaded = True
            logger.info(f"Loaded graph with {len(self.graph)} nodes")

    async def find_best_route(
        self,
        from_stop_id: str,
        to_stop_id: str,
        db: Session,
        max_transfers: int = 3
    ) -> Optional[RouteResponse]:
        """
        Find the best route using Dijkstra with live first-leg overlay
        """
        self._ensure_graph_loaded(db)

        if from_stop_id not in self.graph:
            logger.warning(f"Origin stop {from_stop_id} not found in graph. Graph has {len(self.graph)} nodes")
            return None

        if from_stop_id == to_stop_id:
            return RouteResponse(legs=[], transfers=0, total_eta_s=0, alerts=[])

        # Check if destination exists
        if to_stop_id not in self.graph:
            logger.warning(f"Destination stop {to_stop_id} not found in graph")
            return None

        # Run Dijkstra's algorithm
        logger.info(f"Running Dijkstra from {from_stop_id} to {to_stop_id}")
        path = self._dijkstra(from_stop_id, to_stop_id, max_transfers)

        if not path:
            logger.warning(f"No path found from {from_stop_id} to {to_stop_id}")
            return None

        # Convert path to route legs with live overlay
        legs = await self._path_to_legs(path, db)
        if not legs:
            return None

        # Calculate total time and transfers
        total_eta_s = sum(leg.board_in_s + leg.run_s for leg in legs)
        transfers = sum(1 for leg in legs if leg.transfer)

        # TODO: Get alerts for affected routes
        alerts = []

        return RouteResponse(
            legs=legs,
            transfers=transfers,
            total_eta_s=total_eta_s,
            alerts=alerts
        )

    def _dijkstra(
        self,
        start: str,
        end: str,
        max_transfers: int
    ) -> Optional[List[Tuple[str, str, str, int, bool]]]:
        """
        Dijkstra's algorithm with transfer penalty
        Returns path as list of (from_stop, to_stop, route_id, travel_time, is_transfer)
        """
        # Priority queue: (total_cost, current_stop, transfers_count, path)
        pq = [(0, start, 0, [])]
        visited = set()
        best_costs = defaultdict(lambda: float('inf'))

        while pq:
            cost, current_stop, transfers, path = heapq.heappop(pq)

            # State includes stop and transfer count to allow different paths
            state = (current_stop, transfers)
            if state in visited:
                continue
            visited.add(state)

            # Found destination
            if current_stop == end:
                return path

            # Skip if too many transfers
            if transfers > max_transfers:
                continue

            # Explore neighbors
            for next_stop, connections in self.graph.get(current_stop, {}).items():
                for conn in connections:
                    is_transfer = conn['is_transfer']
                    next_transfers = transfers + (1 if is_transfer else 0)

                    if next_transfers > max_transfers:
                        continue

                    # Calculate edge cost
                    edge_cost = conn['travel_time'] + conn['transfer_penalty']
                    new_cost = cost + edge_cost

                    new_state = (next_stop, next_transfers)
                    if new_cost < best_costs[new_state]:
                        best_costs[new_state] = new_cost

                        new_path = path + [(
                            current_stop,
                            next_stop,
                            conn['route_id'],
                            conn['travel_time'],
                            is_transfer
                        )]

                        heapq.heappush(pq, (new_cost, next_stop, next_transfers, new_path))

        return None

    async def _path_to_legs(
        self,
        path: List[Tuple[str, str, str, int, bool]],
        db: Session
    ) -> Optional[List[RouteLeg]]:
        """Convert Dijkstra path to route legs with live first-leg overlay"""
        if not path:
            return None

        legs = []

        for i, (from_stop, to_stop, route_id, travel_time, is_transfer) in enumerate(path):
            # Skip transfer edges (they don't represent actual travel)
            if is_transfer:
                continue

            # For first leg, try to get live boarding time
            board_in_s = travel_time  # Default to scheduled time
            if i == 0:  # First leg
                live_board_time = await self._get_live_boarding_time(from_stop, route_id)
                if live_board_time is not None:
                    board_in_s = live_board_time

            legs.append(RouteLeg(
                route_id=route_id,
                from_stop_id=from_stop,
                to_stop_id=to_stop,
                board_in_s=board_in_s,
                run_s=travel_time,
                transfer=(i > 0)  # First leg is never a transfer
            ))

        return legs

    async def _get_live_boarding_time(
        self,
        stop_id: str,
        route_id: str
    ) -> Optional[int]:
        """
        Get live boarding time for first leg from cached arrivals
        Returns seconds until next departure, or None if no live data
        """
        try:
            # Try all directions to find arrivals for this route
            for direction in ['N', 'S', 'E', 'W']:
                arrivals = arrivals_cache.get_arrivals(stop_id, direction)
                if not arrivals:
                    continue

                # Find next arrival for this route
                route_arrivals = [a for a in arrivals if a.route_id == route_id]
                if route_arrivals:
                    # Return the ETA of the next train
                    next_arrival = min(route_arrivals, key=lambda a: a.eta_s)
                    return next_arrival.eta_s

            return None

        except Exception as e:
            logger.error(f"Error getting live boarding time for {stop_id} route {route_id}: {e}")
            return None

    def clear_graph_cache(self):
        """Clear the loaded graph cache (for testing or updates)"""
        self.graph = {}
        self.graph_loaded = False


# Global route planner instance
route_planner = RoutePlanner()