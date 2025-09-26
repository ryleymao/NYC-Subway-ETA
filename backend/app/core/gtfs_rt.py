"""
GTFS-RT (Real-time) data fetching and processing
"""
import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone

import httpx
from google.transit import gtfs_realtime_pb2
from google.protobuf.message import DecodeError

from app.core.config import get_settings
from app.core.cache import arrivals_cache
from app.models.dto import Arrival

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


class GTFSRealtimeFetcher:
    """Fetches and processes GTFS-RT data from MTA feeds"""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=settings.api_timeout_seconds)
        self.feed_urls = settings.mta_feed_urls

    async def fetch_all_feeds(self) -> Dict[str, List[Arrival]]:
        """Fetch all GTFS-RT feeds and return processed arrivals"""
        all_arrivals = {}

        # Fetch all feeds concurrently
        tasks = []
        for feed_url in self.feed_urls:
            tasks.append(self._fetch_single_feed(feed_url))

        feed_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for feed_url, result in zip(self.feed_urls, feed_results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching feed {feed_url}: {result}")
                continue

            if result:
                # Merge arrivals from this feed
                for (stop_id, direction), arrivals in result.items():
                    key = (stop_id, direction)
                    if key not in all_arrivals:
                        all_arrivals[key] = []
                    all_arrivals[key].extend(arrivals)

        return all_arrivals

    async def _fetch_single_feed(self, feed_url: str) -> Optional[Dict[Tuple[str, str], List[Arrival]]]:
        """Fetch and parse a single GTFS-RT feed"""
        try:
            logger.debug(f"Fetching GTFS-RT feed: {feed_url}")
            response = await self.client.get(feed_url)
            response.raise_for_status()

            # Parse protobuf
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)

            # Process trip updates into arrivals
            arrivals = self._process_trip_updates(feed)

            logger.debug(f"Processed {len(arrivals)} arrivals from {feed_url}")
            return arrivals

        except DecodeError as e:
            logger.error(f"Failed to decode protobuf from {feed_url}: {e}")
        except httpx.RequestError as e:
            logger.error(f"Network error fetching {feed_url}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error processing {feed_url}: {e}")

        return None

    def _process_trip_updates(self, feed: gtfs_realtime_pb2.FeedMessage) -> Dict[Tuple[str, str], List[Arrival]]:
        """Process GTFS-RT TripUpdates into arrival predictions"""
        arrivals_by_stop = {}
        current_time = datetime.now(timezone.utc)

        for entity in feed.entity:
            if not entity.HasField('trip_update'):
                continue

            trip_update = entity.trip_update
            trip_id = trip_update.trip.trip_id
            route_id = trip_update.trip.route_id

            # Get trip headsign (destination)
            # TODO: Extract this from GTFS static data
            headsign = self._get_headsign_for_trip(trip_id, route_id)

            for stop_time_update in trip_update.stop_time_update:
                stop_id = stop_time_update.stop_id

                # Get direction from stop_id (NYC-specific logic)
                direction = self._infer_direction_from_stop_id(stop_id)
                if not direction:
                    continue

                # Clean stop_id (remove direction suffix if present)
                clean_stop_id = self._clean_stop_id(stop_id)

                # Calculate ETA
                eta_seconds = None
                if stop_time_update.HasField('arrival'):
                    arrival_time = datetime.fromtimestamp(
                        stop_time_update.arrival.time, timezone.utc
                    )
                    eta_seconds = int((arrival_time - current_time).total_seconds())
                elif stop_time_update.HasField('departure'):
                    departure_time = datetime.fromtimestamp(
                        stop_time_update.departure.time, timezone.utc
                    )
                    eta_seconds = int((departure_time - current_time).total_seconds())

                # Skip if no valid ETA or if ETA is negative (already passed)
                if eta_seconds is None or eta_seconds < 0:
                    continue

                # Skip if ETA is too far in the future (> 60 minutes)
                if eta_seconds > 3600:
                    continue

                # Create arrival object
                arrival = Arrival(
                    route_id=route_id,
                    headsign=headsign,
                    eta_s=eta_seconds
                )

                # Group by (stop_id, direction)
                key = (clean_stop_id, direction)
                if key not in arrivals_by_stop:
                    arrivals_by_stop[key] = []
                arrivals_by_stop[key].append(arrival)

        return arrivals_by_stop

    def _get_headsign_for_trip(self, trip_id: str, route_id: str) -> str:
        """Get headsign for a trip (TODO: lookup from GTFS static)"""
        # Simplified implementation - in production, look this up from database
        return f"{route_id} Train"

    def _infer_direction_from_stop_id(self, stop_id: str) -> Optional[str]:
        """
        Infer direction from NYC MTA stop_id format
        NYC uses suffixes like N, S to indicate platform direction
        """
        if stop_id.endswith('N'):
            return 'N'
        elif stop_id.endswith('S'):
            return 'S'
        # TODO: Add more sophisticated logic for E/W directions
        # and complex station configurations
        return None

    def _clean_stop_id(self, stop_id: str) -> str:
        """Remove direction suffix from stop_id to get canonical stop_id"""
        # Remove last character if it's a direction indicator
        if stop_id and stop_id[-1] in ['N', 'S', 'E', 'W']:
            return stop_id[:-1]
        return stop_id

    async def update_cache(self) -> bool:
        """Fetch all feeds and update Redis cache"""
        try:
            logger.info("GTFS-RT fetch started - polling MTA feeds...")
            start_time = datetime.now(timezone.utc)

            # Fetch all feeds
            all_arrivals = await self.fetch_all_feeds()

            # Update cache for each stop+direction
            cache_updates = 0
            total_arrivals = 0
            for (stop_id, direction), arrivals in all_arrivals.items():
                success = arrivals_cache.set_arrivals(
                    stop_id=stop_id,
                    direction=direction,
                    arrivals=arrivals,
                    timestamp=start_time
                )
                if success:
                    cache_updates += 1
                    total_arrivals += len(arrivals)

            # Update feed timestamp
            arrivals_cache.set_feed_update(start_time)

            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(f"Decoded {total_arrivals} trip updates, refreshed {cache_updates} station caches in {elapsed:.1f}s")

            return True

        except Exception as e:
            logger.error(f"GTFS-RT fetch failed: {e}")
            return False

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Background task runner
class GTFSRealtimePoller:
    """Runs GTFS-RT fetching in the background"""

    def __init__(self):
        self.fetcher = GTFSRealtimeFetcher()
        self.is_running = False
        self.task = None

    async def start(self):
        """Start the background polling task"""
        if self.is_running:
            return

        self.is_running = True
        self.task = asyncio.create_task(self._poll_loop())
        logger.info("Started GTFS-RT background poller")

    async def stop(self):
        """Stop the background polling task"""
        if not self.is_running:
            return

        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        await self.fetcher.close()
        logger.info("Stopped GTFS-RT background poller")

    async def _poll_loop(self):
        """Main polling loop"""
        logger.info(f"GTFS-RT poller starting - fetching every {settings.gtfs_rt_poll_interval_seconds} seconds")

        while self.is_running:
            try:
                await self.fetcher.update_cache()
                await asyncio.sleep(settings.gtfs_rt_poll_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in GTFS-RT polling loop: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(30)


# Main entry point for running as a standalone service
async def main():
    """Main function for running the GTFS-RT poller as a standalone service"""
    poller = GTFSRealtimePoller()

    try:
        logger.info("Starting GTFS-RT background service...")
        await poller.start()

        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await poller.stop()
        logger.info("GTFS-RT background service stopped")


if __name__ == "__main__":
    asyncio.run(main())