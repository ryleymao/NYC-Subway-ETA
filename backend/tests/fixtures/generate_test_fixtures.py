#!/usr/bin/env python3
"""
Generate synthetic GTFS and GTFS-RT test fixtures
"""
import csv
import zipfile
from pathlib import Path
from datetime import datetime, timezone
from google.transit import gtfs_realtime_pb2


def create_minimal_gtfs(output_dir: Path):
    """Create minimal GTFS static data for testing"""
    output_dir.mkdir(parents=True, exist_ok=True)

    # agency.txt
    with open(output_dir / "agency.txt", 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'agency_id', 'agency_name', 'agency_url', 'agency_timezone'
        ])
        writer.writeheader()
        writer.writerow({
            'agency_id': 'TEST_AGENCY',
            'agency_name': 'Test Transit Agency',
            'agency_url': 'https://example.com',
            'agency_timezone': 'America/New_York'
        })

    # routes.txt
    with open(output_dir / "routes.txt", 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'route_id', 'agency_id', 'route_short_name', 'route_long_name',
            'route_type', 'route_color'
        ])
        writer.writeheader()
        writer.writerows([
            {
                'route_id': 'TEST_N',
                'agency_id': 'TEST_AGENCY',
                'route_short_name': 'N',
                'route_long_name': 'Test Broadway Express',
                'route_type': 1,
                'route_color': 'FCCC0A'
            },
            {
                'route_id': 'TEST_Q',
                'agency_id': 'TEST_AGENCY',
                'route_short_name': 'Q',
                'route_long_name': 'Test Broadway Express',
                'route_type': 1,
                'route_color': 'FCCC0A'
            }
        ])

    # stops.txt
    with open(output_dir / "stops.txt", 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'stop_id', 'stop_name', 'stop_lat', 'stop_lon', 'location_type'
        ])
        writer.writeheader()
        writer.writerows([
            {
                'stop_id': 'TEST_001',
                'stop_name': 'Test Station A',
                'stop_lat': 40.7589,
                'stop_lon': -73.9851,
                'location_type': 0
            },
            {
                'stop_id': 'TEST_002',
                'stop_name': 'Test Station B',
                'stop_lat': 40.7505,
                'stop_lon': -73.9934,
                'location_type': 0
            },
            {
                'stop_id': 'TEST_003',
                'stop_name': 'Test Station C',
                'stop_lat': 40.7424,
                'stop_lon': -73.9878,
                'location_type': 0
            }
        ])

    # calendar.txt
    with open(output_dir / "calendar.txt", 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'service_id', 'monday', 'tuesday', 'wednesday', 'thursday',
            'friday', 'saturday', 'sunday', 'start_date', 'end_date'
        ])
        writer.writeheader()
        writer.writerow({
            'service_id': 'TEST_WEEKDAY',
            'monday': 1, 'tuesday': 1, 'wednesday': 1, 'thursday': 1,
            'friday': 1, 'saturday': 0, 'sunday': 0,
            'start_date': '20240101', 'end_date': '20241231'
        })

    # trips.txt
    with open(output_dir / "trips.txt", 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'trip_id', 'route_id', 'service_id', 'trip_headsign', 'direction_id'
        ])
        writer.writeheader()
        writer.writerows([
            {
                'trip_id': 'TEST_N_001',
                'route_id': 'TEST_N',
                'service_id': 'TEST_WEEKDAY',
                'trip_headsign': 'Test Terminal North',
                'direction_id': 0
            },
            {
                'trip_id': 'TEST_Q_001',
                'route_id': 'TEST_Q',
                'service_id': 'TEST_WEEKDAY',
                'trip_headsign': 'Test Terminal East',
                'direction_id': 0
            }
        ])

    # stop_times.txt
    with open(output_dir / "stop_times.txt", 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'trip_id', 'arrival_time', 'departure_time', 'stop_id', 'stop_sequence'
        ])
        writer.writeheader()
        writer.writerows([
            # N train
            {
                'trip_id': 'TEST_N_001',
                'arrival_time': '08:00:00',
                'departure_time': '08:00:30',
                'stop_id': 'TEST_001',
                'stop_sequence': 1
            },
            {
                'trip_id': 'TEST_N_001',
                'arrival_time': '08:03:00',
                'departure_time': '08:03:30',
                'stop_id': 'TEST_002',
                'stop_sequence': 2
            },
            {
                'trip_id': 'TEST_N_001',
                'arrival_time': '08:06:00',
                'departure_time': '08:06:30',
                'stop_id': 'TEST_003',
                'stop_sequence': 3
            },
            # Q train
            {
                'trip_id': 'TEST_Q_001',
                'arrival_time': '08:02:00',
                'departure_time': '08:02:30',
                'stop_id': 'TEST_001',
                'stop_sequence': 1
            },
            {
                'trip_id': 'TEST_Q_001',
                'arrival_time': '08:05:00',
                'departure_time': '08:05:30',
                'stop_id': 'TEST_002',
                'stop_sequence': 2
            }
        ])

    # transfers.txt
    with open(output_dir / "transfers.txt", 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'from_stop_id', 'to_stop_id', 'transfer_type', 'min_transfer_time'
        ])
        writer.writeheader()
        writer.writerow({
            'from_stop_id': 'TEST_002',
            'to_stop_id': 'TEST_002',
            'transfer_type': 2,
            'min_transfer_time': 180
        })

    print(f"Created minimal GTFS data in {output_dir}")


def create_gtfs_rt_fixture(output_path: Path):
    """Create synthetic GTFS-RT protobuf fixture"""
    # Create GTFS-RT feed message
    feed = gtfs_realtime_pb2.FeedMessage()

    # Set header
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = int(datetime.now(timezone.utc).timestamp())

    # Add trip update entity
    entity = feed.entity.add()
    entity.id = "TEST_N_001_update"

    # Trip update
    trip_update = entity.trip_update
    trip_update.trip.trip_id = "TEST_N_001"
    trip_update.trip.route_id = "TEST_N"

    # Current timestamp for calculations
    now_ts = int(datetime.now(timezone.utc).timestamp())

    # Stop time updates
    stop_updates = [
        ("TEST_001N", now_ts + 120),  # 2 minutes from now
        ("TEST_002N", now_ts + 300),  # 5 minutes from now
        ("TEST_003N", now_ts + 480),  # 8 minutes from now
    ]

    for stop_id, arrival_time in stop_updates:
        stu = trip_update.stop_time_update.add()
        stu.stop_id = stop_id
        stu.arrival.time = arrival_time

    # Add another trip (Q train)
    entity2 = feed.entity.add()
    entity2.id = "TEST_Q_001_update"

    trip_update2 = entity2.trip_update
    trip_update2.trip.trip_id = "TEST_Q_001"
    trip_update2.trip.route_id = "TEST_Q"

    # Q train stop updates
    q_stop_updates = [
        ("TEST_001N", now_ts + 180),  # 3 minutes from now
        ("TEST_002N", now_ts + 360),  # 6 minutes from now
    ]

    for stop_id, arrival_time in q_stop_updates:
        stu = trip_update2.stop_time_update.add()
        stu.stop_id = stop_id
        stu.arrival.time = arrival_time

    # Write to file
    with open(output_path, 'wb') as f:
        f.write(feed.SerializeToString())

    print(f"Created GTFS-RT fixture at {output_path}")


def create_gtfs_zip(gtfs_dir: Path, zip_path: Path):
    """Create zip file from GTFS directory"""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in gtfs_dir.glob("*.txt"):
            zipf.write(file, file.name)

    print(f"Created GTFS zip at {zip_path}")


def main():
    """Generate all test fixtures"""
    fixtures_dir = Path(__file__).parent
    gtfs_dir = fixtures_dir / "sample_gtfs"

    # Create GTFS static data
    create_minimal_gtfs(gtfs_dir)

    # Create GTFS zip
    create_gtfs_zip(gtfs_dir, fixtures_dir / "sample_gtfs.zip")

    # Create GTFS-RT fixture
    create_gtfs_rt_fixture(fixtures_dir / "sample_gtfs_rt.bin")

    print("All test fixtures created successfully!")


if __name__ == "__main__":
    main()