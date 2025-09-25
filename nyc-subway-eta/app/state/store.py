import json
import time
from typing import List, Dict, DefaultDict
from collections import defaultdict

from .config import REDIS_URL, STORE_BACKEND
from ..service.schemas import Arrival

KEY_PREFIX = "arrivals:"  # arrivals:<stop_id>

# In-memory backend (for Codespaces without Docker/Redis)
_memory: DefaultDict[str, List[str]] = defaultdict(list)

class ArrivalStore:
    def __init__(self):
        self.backend = STORE_BACKEND
        self._redis = None
        if self.backend == "redis":
            import redis.asyncio as redis  # lazy import so memory mode works with no redis install running
            self._redis = redis.from_url(REDIS_URL, decode_responses=True)

    async def get_arrivals(self, stop_id: str, limit: int = 3) -> List[Arrival]:
        if self.backend == "redis" and self._redis:
            data = await self._redis.lrange(f"{KEY_PREFIX}{stop_id}", 0, limit - 1)
        else:
            data = _memory[f"{KEY_PREFIX}{stop_id}"][:limit]

        items = [Arrival.model_validate_json(x) for x in data]
        now = int(time.time())
        return [it for it in items if it.arrival_epoch >= now - 90]

    async def put_arrivals(self, stop_id: str, arrivals: List[Arrival]):
        key = f"{KEY_PREFIX}{stop_id}"
        payloads = [a.model_dump_json() for a in arrivals][:10]
        if self.backend == "redis" and self._redis:
            pipe = self._redis.pipeline()
            await pipe.delete(key)
            for p in payloads:
                await pipe.rpush(key, p)
            await pipe.ltrim(key, 0, 9)
            await pipe.execute()
        else:
            _memory[key] = payloads
