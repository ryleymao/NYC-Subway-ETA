import os
import time
import httpx
from dotenv import load_dotenv
from google.transit import gtfs_realtime_pb2  # from gtfs-realtime-bindings

load_dotenv()

GTFS_TRIP_UPDATES_URL = os.getenv("MTA_GTFS_TRIP_UPDATES_URL", "")
MTA_API_KEY = os.getenv("MTA_API_KEY", "")

def fetch_trip_updates():
    if not GTFS_TRIP_UPDATES_URL or not MTA_API_KEY:
        raise RuntimeError("Set MTA_GTFS_TRIP_UPDATES_URL and MTA_API_KEY in your environment")
    headers = {"x-api-key": MTA_API_KEY}
    t0 = time.time()
    r = httpx.get(GTFS_TRIP_UPDATES_URL, headers=headers, timeout=15)
    r.raise_for_status()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(r.content)
    age = time.time() - t0
    return feed, age

if __name__ == "__main__":
    feed, age = fetch_trip_updates()
    trips = 0
    stu_count = 0
    for ent in feed.entity:
        if ent.HasField("trip_update"):
            trips += 1
            stu_count += len(ent.trip_update.stop_time_update)
    print(f"Fetched {trips} trips with {stu_count} stop_time_updates in {age:.2f}s")
