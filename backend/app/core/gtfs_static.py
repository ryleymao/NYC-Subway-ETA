"""
GTFS static data loading and management
"""
import csv
import logging
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, date, time

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from app.models.models import (
    Agency, Route, Stop, Calendar, CalendarDate,
    Trip, StopTime, Transfer, Shape
)

logger = logging.getLogger(__name__)


class GTFSStaticLoader:
    """Loads GTFS static data from CSV files into database"""

    def __init__(self, gtfs_path: str):
        self.gtfs_path = Path(gtfs_path)

    def load_all(self, db: Session) -> Dict[str, int]:
        """Load all GTFS static files into database"""
        counts = {}

        # Order matters due to foreign key constraints
        load_order = [
            ("agency.txt", self._load_agencies),
            ("routes.txt", self._load_routes),
            ("stops.txt", self._load_stops),
            ("calendar.txt", self._load_calendar),
            ("calendar_dates.txt", self._load_calendar_dates),
            ("trips.txt", self._load_trips),
            ("stop_times.txt", self._load_stop_times),
            ("transfers.txt", self._load_transfers),
            ("shapes.txt", self._load_shapes),
        ]

        for filename, loader_func in load_order:
            file_path = self.gtfs_path / filename
            if file_path.exists():
                logger.info(f"Loading {filename}...")
                try:
                    count = loader_func(db, file_path)
                    counts[filename] = count
                    logger.info(f"Loaded {count} records from {filename}")
                except Exception as e:
                    logger.error(f"Failed to load {filename}: {e}")
                    counts[filename] = 0
            else:
                logger.warning(f"File not found: {filename}")
                counts[filename] = 0

        db.commit()
        return counts

    def _load_agencies(self, db: Session, file_path: Path) -> int:
        """Load agencies from agency.txt"""
        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            batch = []
            for row in reader:
                batch.append(Agency(
                    agency_id=row['agency_id'],
                    agency_name=row['agency_name'],
                    agency_url=row['agency_url'],
                    agency_timezone=row['agency_timezone'],
                    agency_lang=row.get('agency_lang')
                ))
                if len(batch) >= 1000:
                    db.add_all(batch)
                    db.flush()
                    count += len(batch)
                    batch = []

            if batch:
                db.add_all(batch)
                count += len(batch)

        return count

    def _load_routes(self, db: Session, file_path: Path) -> int:
        """Load routes from routes.txt"""
        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            batch = []
            for row in reader:
                batch.append(Route(
                    route_id=row['route_id'],
                    agency_id=row.get('agency_id'),
                    route_short_name=row.get('route_short_name'),
                    route_long_name=row.get('route_long_name'),
                    route_desc=row.get('route_desc'),
                    route_type=int(row['route_type']),
                    route_url=row.get('route_url'),
                    route_color=row.get('route_color'),
                    route_text_color=row.get('route_text_color')
                ))
                if len(batch) >= 1000:
                    db.add_all(batch)
                    db.flush()
                    count += len(batch)
                    batch = []

            if batch:
                db.add_all(batch)
                count += len(batch)

        return count

    def _load_stops(self, db: Session, file_path: Path) -> int:
        """Load stops from stops.txt"""
        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            batch = []
            for row in reader:
                batch.append(Stop(
                    stop_id=row['stop_id'],
                    stop_code=row.get('stop_code'),
                    stop_name=row['stop_name'],
                    stop_desc=row.get('stop_desc'),
                    stop_lat=float(row['stop_lat']),
                    stop_lon=float(row['stop_lon']),
                    zone_id=row.get('zone_id'),
                    stop_url=row.get('stop_url'),
                    location_type=int(row.get('location_type', 0)),
                    parent_station=row.get('parent_station')
                ))
                if len(batch) >= 1000:
                    db.add_all(batch)
                    db.flush()
                    count += len(batch)
                    batch = []

            if batch:
                db.add_all(batch)
                count += len(batch)

        return count

    def _load_calendar(self, db: Session, file_path: Path) -> int:
        """Load calendar from calendar.txt"""
        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            batch = []
            for row in reader:
                batch.append(Calendar(
                    service_id=row['service_id'],
                    monday=bool(int(row['monday'])),
                    tuesday=bool(int(row['tuesday'])),
                    wednesday=bool(int(row['wednesday'])),
                    thursday=bool(int(row['thursday'])),
                    friday=bool(int(row['friday'])),
                    saturday=bool(int(row['saturday'])),
                    sunday=bool(int(row['sunday'])),
                    start_date=datetime.strptime(row['start_date'], '%Y%m%d').date(),
                    end_date=datetime.strptime(row['end_date'], '%Y%m%d').date()
                ))
                if len(batch) >= 1000:
                    db.add_all(batch)
                    db.flush()
                    count += len(batch)
                    batch = []

            if batch:
                db.add_all(batch)
                count += len(batch)

        return count

    def _load_calendar_dates(self, db: Session, file_path: Path) -> int:
        """Load calendar dates from calendar_dates.txt"""
        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            batch = []
            for row in reader:
                batch.append(CalendarDate(
                    service_id=row['service_id'],
                    date=datetime.strptime(row['date'], '%Y%m%d').date(),
                    exception_type=int(row['exception_type'])
                ))
                if len(batch) >= 1000:
                    db.add_all(batch)
                    db.flush()
                    count += len(batch)
                    batch = []

            if batch:
                db.add_all(batch)
                count += len(batch)

        return count

    def _load_trips(self, db: Session, file_path: Path) -> int:
        """Load trips from trips.txt"""
        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            batch = []
            for row in reader:
                batch.append(Trip(
                    trip_id=row['trip_id'],
                    route_id=row['route_id'],
                    service_id=row['service_id'],
                    trip_headsign=row.get('trip_headsign'),
                    trip_short_name=row.get('trip_short_name'),
                    direction_id=int(row['direction_id']) if row.get('direction_id') else None,
                    block_id=row.get('block_id'),
                    shape_id=row.get('shape_id')
                ))
                if len(batch) >= 1000:
                    db.add_all(batch)
                    db.flush()
                    count += len(batch)
                    batch = []

            if batch:
                db.add_all(batch)
                count += len(batch)

        return count

    def _load_stop_times(self, db: Session, file_path: Path) -> int:
        """Load stop times from stop_times.txt (this can be very large)"""
        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            batch = []
            for row in reader:
                batch.append(StopTime(
                    trip_id=row['trip_id'],
                    arrival_time=row.get('arrival_time'),
                    departure_time=row.get('departure_time'),
                    stop_id=row['stop_id'],
                    stop_sequence=int(row['stop_sequence']),
                    stop_headsign=row.get('stop_headsign'),
                    pickup_type=int(row.get('pickup_type', 0)),
                    drop_off_type=int(row.get('drop_off_type', 0)),
                    shape_dist_traveled=float(row['shape_dist_traveled']) if row.get('shape_dist_traveled') else None
                ))

                # Use smaller batches for stop_times due to size
                if len(batch) >= 500:
                    db.add_all(batch)
                    db.flush()
                    count += len(batch)
                    batch = []
                    if count % 10000 == 0:
                        logger.info(f"Loaded {count} stop times so far...")

            if batch:
                db.add_all(batch)
                count += len(batch)

        return count

    def _load_transfers(self, db: Session, file_path: Path) -> int:
        """Load transfers from transfers.txt"""
        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            batch = []
            for row in reader:
                batch.append(Transfer(
                    from_stop_id=row['from_stop_id'],
                    to_stop_id=row['to_stop_id'],
                    transfer_type=int(row['transfer_type']),
                    min_transfer_time=int(row['min_transfer_time']) if row.get('min_transfer_time') else None
                ))
                if len(batch) >= 1000:
                    db.add_all(batch)
                    db.flush()
                    count += len(batch)
                    batch = []

            if batch:
                db.add_all(batch)
                count += len(batch)

        return count

    def _load_shapes(self, db: Session, file_path: Path) -> int:
        """Load shapes from shapes.txt"""
        count = 0
        if not file_path.exists():
            return 0

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            batch = []
            for row in reader:
                batch.append(Shape(
                    shape_id=row['shape_id'],
                    shape_pt_lat=float(row['shape_pt_lat']),
                    shape_pt_lon=float(row['shape_pt_lon']),
                    shape_pt_sequence=int(row['shape_pt_sequence']),
                    shape_dist_traveled=float(row['shape_dist_traveled']) if row.get('shape_dist_traveled') else None
                ))
                if len(batch) >= 1000:
                    db.add_all(batch)
                    db.flush()
                    count += len(batch)
                    batch = []

            if batch:
                db.add_all(batch)
                count += len(batch)

        return count

    def extract_zip(self, zip_path: str) -> Path:
        """Extract GTFS zip file to directory"""
        zip_path = Path(zip_path)
        extract_path = self.gtfs_path

        logger.info(f"Extracting {zip_path} to {extract_path}")
        extract_path.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)

        return extract_path