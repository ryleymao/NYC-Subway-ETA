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

    def _get_directional_stop_ids(self, base_stop_id: str) -> List[str]:
        """Get all directional variations of a stop ID that exist in the graph"""
        # If the stop ID already has a direction, return it
        if base_stop_id.endswith(('N', 'S', 'E', 'W')):
            return [base_stop_id] if base_stop_id in self.graph else []

        # Try all possible directions
        possible_ids = [
            f"{base_stop_id}N",
            f"{base_stop_id}S",
            f"{base_stop_id}E",
            f"{base_stop_id}W"
        ]

        return [stop_id for stop_id in possible_ids if stop_id in self.graph]

    async def find_best_route(
        self,
        from_stop_id: str,
        to_stop_id: str,
        db: Session,
        max_transfers: int = 3
    ) -> Optional[RouteResponse]:
        """
        Find the best route using Dijkstra with live first-leg overlay
        Handles both base stop IDs (e.g., "127") and directional IDs (e.g., "127N")
        """
        self._ensure_graph_loaded(db)

        # Get all possible directional variations of the origin and destination
        from_options = self._get_directional_stop_ids(from_stop_id)
        to_options = self._get_directional_stop_ids(to_stop_id)

        logger.info(f"From stop {from_stop_id} has options: {from_options}")
        logger.info(f"To stop {to_stop_id} has options: {to_options}")

        if not from_options:
            logger.warning(f"Origin stop {from_stop_id} not found in graph. Graph has {len(self.graph)} nodes")
            return None

        if not to_options:
            logger.warning(f"Destination stop {to_stop_id} not found in graph")
            return None

        if from_stop_id == to_stop_id:
            return RouteResponse(legs=[], transfers=0, total_eta_s=0, alerts=[])

        # Try all combinations of origin and destination directions to find the best route
        best_route = None
        best_cost = float('inf')

        for from_dir in from_options:
            for to_dir in to_options:
                # Skip if same exact stop
                if from_dir == to_dir:
                    continue

                # For platform transfers within same station, allow if different directions
                base_from = from_dir.rstrip('NSEW')
                base_to = to_dir.rstrip('NSEW')
                if base_from == base_to and from_dir != to_dir:
                    # This is a platform transfer - allow it but process specially
                    pass

                logger.info(f"Trying route from {from_dir} to {to_dir}")
                path = self._dijkstra(from_dir, to_dir, max_transfers)

                if path:
                    # Calculate total cost for this path
                    total_cost = sum(edge[3] for edge in path)  # edge[3] is travel_time

                    if total_cost < best_cost:
                        best_cost = total_cost
                        best_route = path
                        logger.info(f"Found better route from {from_dir} to {to_dir} with cost {total_cost}")

        if not best_route:
            logger.warning(f"No path found from {from_stop_id} to {to_stop_id}")
            return None

        # Convert path to route legs with live overlay
        legs = await self._path_to_legs(best_route, db)
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

            # Get station names and create instruction
            from_name = await self._get_stop_name(from_stop, db)
            to_name = await self._get_stop_name(to_stop, db)
            direction = self._get_direction_name(from_stop, to_stop)
            line_color = self._get_line_color(route_id)
            instruction = self._create_instruction(route_id, from_name, to_name, direction, board_in_s, travel_time, (i > 0))

            legs.append(RouteLeg(
                route_id=route_id,
                from_stop_id=from_stop,
                to_stop_id=to_stop,
                from_stop_name=from_name,
                to_stop_name=to_name,
                board_in_s=board_in_s,
                run_s=travel_time,
                transfer=(i > 0),  # First leg is never a transfer
                direction=direction,
                line_color=line_color,
                instruction=instruction
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

    async def get_station_status(self, stop_id: str) -> dict:
        """Get station operational status and accessibility info"""
        try:
            # This could be expanded to include real MTA service alerts
            return {
                "operational": True,
                "accessible": True,  # Could be enhanced with GTFS accessibility data
                "alerts": []
            }
        except Exception as e:
            logger.error(f"Error getting station status for {stop_id}: {e}")
            return {"operational": False, "accessible": False, "alerts": []}

    async def _get_stop_name(self, stop_id: str, db: Session) -> str:
        """Get the human-readable name for a stop"""
        try:
            # Remove directional suffix to get base stop ID
            base_stop_id = stop_id.rstrip('NSEW')

            from app.models.models import Stop
            stop = db.query(Stop).filter(Stop.stop_id == base_stop_id).first()
            if stop and stop.stop_name:
                return stop.stop_name
            return f"Station {base_stop_id}"
        except Exception as e:
            logger.error(f"Error getting stop name for {stop_id}: {e}")
            return f"Station {stop_id}"

    def _get_direction_name(self, from_stop: str, to_stop: str) -> str:
        """Get human-readable direction name"""
        from_dir = from_stop[-1] if from_stop.endswith(('N', 'S', 'E', 'W')) else ''
        to_dir = to_stop[-1] if to_stop.endswith(('N', 'S', 'E', 'W')) else ''

        if from_dir == 'N' or to_dir == 'N':
            return "Uptown"
        elif from_dir == 'S' or to_dir == 'S':
            return "Downtown"
        elif from_dir == 'E' or to_dir == 'E':
            return "Eastbound"
        elif from_dir == 'W' or to_dir == 'W':
            return "Westbound"
        else:
            return "Continuing"

    def _get_line_color(self, route_id: str) -> str:
        """Get the official MTA color for a subway line"""
        line_colors = {
            # IRT Lexington Avenue Line
            '4': '#00933C', '5': '#00933C', '6': '#00933C', '6X': '#00933C',
            # IRT Broadway-Seventh Avenue Line
            '1': '#EE352E', '2': '#EE352E', '3': '#EE352E',
            # IRT Flushing Line
            '7': '#B933AD', '7X': '#B933AD',
            # BMT Broadway Line
            'N': '#FCCC0A', 'Q': '#FCCC0A', 'R': '#FCCC0A', 'W': '#FCCC0A',
            # BMT Brighton Line
            'B': '#FF6319', 'D': '#FF6319', 'F': '#FF6319', 'M': '#FF6319',
            # IND Eighth Avenue Line
            'A': '#0039A6', 'C': '#0039A6', 'E': '#0039A6',
            # BMT Canarsie Line
            'L': '#A7A9AC',
            # IND Queens Boulevard Line
            'V': '#FF6319',
            # Shuttles
            'S': '#808183',
            # SIR
            'SI': '#0039A6',
            # JFK AirTrain
            'H': '#0039A6',
            # Default for unknown routes
            'TRANSFER': '#6D6E71'
        }
        return line_colors.get(route_id, '#6D6E71')

    def _create_instruction(self, route_id: str, from_name: str, to_name: str,
                          direction: str, board_in_s: int, travel_time: int, is_transfer: bool) -> str:
        """Create human-readable instruction for this leg"""

        if route_id == 'TRANSFER':
            transfer_time = board_in_s // 60
            return f"Transfer to another line ({transfer_time} min walk)"

        if route_id == 'PLATFORM_TRANSFER':
            transfer_time = board_in_s // 60
            return f"Change platforms at {from_name} ({transfer_time} min walk)"

        # Format times
        wait_min = board_in_s // 60
        wait_sec = board_in_s % 60
        travel_min = travel_time // 60
        travel_sec = travel_time % 60

        # Create wait time description
        if wait_min > 0:
            wait_desc = f"{wait_min} min" + (f" {wait_sec}s" if wait_sec > 0 else "")
        else:
            wait_desc = f"{wait_sec}s"

        # Create travel time description
        if travel_min > 0:
            travel_desc = f"{travel_min} min" + (f" {travel_sec}s" if travel_sec > 0 else "")
        else:
            travel_desc = f"{travel_sec}s"

        if is_transfer:
            return f"Transfer to {route_id} train {direction.lower()} to {to_name} ({travel_desc} ride, next train in {wait_desc})"
        else:
            return f"Take {route_id} train {direction.lower()} to {to_name} ({travel_desc} ride, next train in {wait_desc})"

    def clear_graph_cache(self):
        """Clear the loaded graph cache (for testing or updates)"""
        self.graph = {}
        self.graph_loaded = False


# Global route planner instance
route_planner = RoutePlanner()