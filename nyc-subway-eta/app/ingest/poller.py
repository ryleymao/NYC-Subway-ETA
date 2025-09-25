import asyncio, time, httpx
from typing import List, Dict
from google.transit import gtfs_realtime_pb2  # from gtfs-realtime-bindings
from ..state.config import MTA_FEED_URLS, POLL_SECONDS
from ..state.store import ArrivalStore
from ..service.schemas import Arrival

async def fetch_feed(client: httpx.AsyncClient, url: str) -> bytes:
    resp = await client.get(url, timeout=20.0)
    resp.raise_for_status()
    return resp.content

def parse_trip_updates(binary: bytes) -> List[Arrival]:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(binary)
    now = int(time.time())
    arrivals: List[Arrival] = []
    for entity in feed.entity:
        tu = entity.trip_update
        if not tu or not tu.stop_time_update:
            continue
        trip_id = tu.trip.trip_id
        route_id = tu.trip.route_id
        headsign = tu.trip.trip_id.split("_")[0] if tu.trip.trip_id else route_id
        for stu in tu.stop_time_update:
            if not (stu.arrival and stu.arrival.time):
                continue
            arrivals.append(Arrival(
                route_id=route_id,
                trip_id=trip_id,
                stop_id=stu.stop_id,
                headsign=headsign,
                arrival_epoch=int(stu.arrival.time),
                scheduled_epoch=int(stu.schedule_relationship) if stu.HasField("schedule_relationship") else None,
                is_approaching=False if not stu.arrival.time else (int(stu.arrival.time) - now) < 120
            ))
    return arrivals

async def run_poller():
    store = ArrivalStore()
    async with httpx.AsyncClient() as client:
        while True:
            try:
                all_arrivals: Dict[str, List[Arrival]] = {}
                for url in MTA_FEED_URLS:
                    binary = await fetch_feed(client, url)
                    parsed = parse_trip_updates(binary)
                    for a in parsed:
                        all_arrivals.setdefault(a.stop_id, []).append(a)
                # Sort per stop_id by soonest arrival
                for stop_id, arrs in all_arrivals.items():
                    arrs.sort(key=lambda a: a.arrival_epoch)
                    await store.put_arrivals(stop_id, arrs[:10])
            except Exception as e:
                # In production you'd log this
                pass
            await asyncio.sleep(POLL_SECONDS)

if __name__ == "__main__":
    asyncio.run(run_poller())
