import os
from dotenv import load_dotenv
load_dotenv()

MTA_FEED_URLS = [u.strip() for u in os.getenv("MTA_FEED_URLS", "").split(",") if u.strip()]
GTFS_STATIC_PATH = os.getenv("GTFS_STATIC_PATH", "./data/gtfs_static")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "30"))
STORE_BACKEND = os.getenv("STORE_BACKEND", "memory").lower()  # "memory" or "redis"
