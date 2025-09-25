import json
import time
from typing import List
import redis.asyncio as redis
from .config import REDIS_URL
from ..service.schemas import Arrival

KEY_PREFIX = "arrivals:"  # arrivals:<stop_id>

class ArrivalStore:
    def __init__(self):
        self.r = redis.from_url(REDIS_URL, decode_responses=True)

    async def get_arrivals(self, stop_id: str, limit: int = 3) -> List[Arrival]:
        data = await self.r.lrange(f"{KEY_PREFIX}{stop_id}", 0, limit-1)
        items = [Arrival.model_validate_json(x) for x in data]
        # Filter out stale predictions (already passed by > 90s)
        now = int(time.time())
        items = [it for it in items if it.arrival_epoch >= now - 90]
        return items

    async def put_arrivals(self, stop_id: str, arrivals: List[Arrival]):
        key = f"{KEY_PREFIX}{stop_id}"
        pipe = self.r.pipeline()
        await pipe.delete(key)
        for a in arrivals:
            await pipe.rpush(key, a.model_dump_json())
        # Keep lists short to limit memory
        await pipe.ltrim(key, 0, 9)
        await pipe.execute()
