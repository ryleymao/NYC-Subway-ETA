import asyncio, time
from app.state.store import ArrivalStore
from app.service.schemas import Arrival

STOP_IDS = ["R23N", "R23S"]

def mk(route, trip, stop, in_sec, now):
    return Arrival(
        route_id=route,
        trip_id=trip,
        stop_id=stop,
        headsign=f"{route} to Downtown",
        arrival_epoch=now + in_sec,
        scheduled_epoch=None,
        is_approaching=in_sec < 120,
    )

async def main():
    store = ArrivalStore()
    now = int(time.time())
    for stop in STOP_IDS:
        arrs = [
            mk("N", f"trip-{stop}-1", stop, 90, now),
            mk("N", f"trip-{stop}-2", stop, 240, now),
            mk("R", f"trip-{stop}-3", stop, 420, now),
        ]
        await store.put_arrivals(stop, arrs)
    print("Seeded mock arrivals for:", ", ".join(STOP_IDS))

if __name__ == "__main__":
    asyncio.run(main())
