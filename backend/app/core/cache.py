"""
Redis cache management for real-time arrivals
"""
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

import redis
from redis import Redis

from app.core.config import get_settings
from app.models.dto import Arrival

logger = logging.getLogger(__name__)

settings = get_settings()

# Global Redis connection
_redis_client: Optional[Redis] = None


def get_redis() -> Redis:
    """Get Redis client instance"""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        logger.info(f"Connected to Redis at {settings.redis_url}")
    return _redis_client


class ArrivalsCache:
    """Cache manager for real-time subway arrivals"""

    def __init__(self):
        self.redis = get_redis()
        self.ttl = settings.redis_ttl_seconds

    def _make_key(self, stop_id: str, direction: str) -> str:
        """Generate Redis key for stop+direction"""
        return f"arrivals:{stop_id}:{direction}"

    def get_arrivals(self, stop_id: str, direction: str) -> Optional[List[Arrival]]:
        """Get cached arrivals for a stop+direction"""
        try:
            key = self._make_key(stop_id, direction)
            data = self.redis.get(key)
            if not data:
                return None

            arrivals_data = json.loads(data)
            return [Arrival(**arrival) for arrival in arrivals_data["arrivals"]]

        except Exception as e:
            logger.error(f"Error getting arrivals from cache: {e}")
            return None

    def set_arrivals(
        self,
        stop_id: str,
        direction: str,
        arrivals: List[Arrival],
        timestamp: datetime = None
    ) -> bool:
        """Cache arrivals for a stop+direction"""
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)

            key = self._make_key(stop_id, direction)
            data = {
                "arrivals": [arrival.model_dump() for arrival in arrivals],
                "as_of_ts": int(timestamp.timestamp()),
                "cached_at": int(datetime.now(timezone.utc).timestamp())
            }

            self.redis.setex(key, self.ttl, json.dumps(data))
            return True

        except Exception as e:
            logger.error(f"Error setting arrivals in cache: {e}")
            return False

    def get_feed_age(self) -> Optional[int]:
        """Get age of the most recent feed update in seconds"""
        try:
            timestamp = self.redis.get("feed:last_update")
            if not timestamp:
                return None

            last_update = datetime.fromtimestamp(float(timestamp), timezone.utc)
            age_seconds = int((datetime.now(timezone.utc) - last_update).total_seconds())
            return age_seconds

        except Exception as e:
            logger.error(f"Error getting feed age: {e}")
            return None

    def set_feed_update(self, timestamp: datetime = None) -> bool:
        """Update the feed last update timestamp"""
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)

            self.redis.set("feed:last_update", int(timestamp.timestamp()))
            return True

        except Exception as e:
            logger.error(f"Error setting feed update timestamp: {e}")
            return False

    def get_all_stops_with_arrivals(self) -> List[str]:
        """Get all stop IDs that have cached arrivals"""
        try:
            keys = self.redis.keys("arrivals:*")
            stops = set()
            for key in keys:
                # Extract stop_id from key format "arrivals:stop_id:direction"
                parts = key.split(":")
                if len(parts) >= 3:
                    stops.add(parts[1])
            return list(stops)

        except Exception as e:
            logger.error(f"Error getting stops with arrivals: {e}")
            return []

    def health_check(self) -> Dict[str, Any]:
        """Perform Redis health check"""
        try:
            # Test basic connectivity
            self.redis.ping()

            # Get some stats
            info = self.redis.info()
            connected_clients = info.get('connected_clients', 0)
            used_memory = info.get('used_memory_human', 'unknown')

            # Count cached arrivals
            arrival_keys = len(self.redis.keys("arrivals:*"))

            return {
                "status": "healthy",
                "connected_clients": connected_clients,
                "used_memory": used_memory,
                "cached_arrivals": arrival_keys,
                "feed_age_seconds": self.get_feed_age()
            }

        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Global cache instance
arrivals_cache = ArrivalsCache()