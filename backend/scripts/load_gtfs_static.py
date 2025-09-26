#!/usr/bin/env python3
"""
Script to download and load GTFS static data into PostgreSQL
Usage: python scripts/load_gtfs_static.py [--download] [--gtfs-path PATH]
"""
import argparse
import logging
import sys
import zipfile
from pathlib import Path
from typing import Optional

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.core.database import Base, create_tables
from app.core.gtfs_static import GTFSStaticLoader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def download_gtfs_static(url: str, output_path: Path) -> bool:
    """Download GTFS static zip file"""
    try:
        logger.info(f"Downloading GTFS static data from {url}")

        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.get(url)
            response.raise_for_status()

            with open(output_path, 'wb') as f:
                f.write(response.content)

            logger.info(f"Downloaded GTFS data to {output_path}")
            return True

    except Exception as e:
        logger.error(f"Failed to download GTFS data: {e}")
        return False


def extract_gtfs_zip(zip_path: Path, extract_path: Path) -> bool:
    """Extract GTFS zip file"""
    try:
        logger.info(f"Extracting {zip_path} to {extract_path}")
        extract_path.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)

        logger.info("Extraction completed")
        return True

    except Exception as e:
        logger.error(f"Failed to extract GTFS data: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Load GTFS static data into database")
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download GTFS data from MTA before loading"
    )
    parser.add_argument(
        "--gtfs-path",
        type=Path,
        default=None,
        help="Path to GTFS data directory (default from settings)"
    )
    parser.add_argument(
        "--zip-path",
        type=Path,
        default=Path("./data/gtfs_static.zip"),
        help="Path for downloaded zip file"
    )
    parser.add_argument(
        "--create-tables",
        action="store_true",
        help="Create database tables before loading"
    )

    args = parser.parse_args()

    # Get settings
    settings = get_settings()

    # Determine GTFS path
    gtfs_path = args.gtfs_path or Path(settings.gtfs_static_path)

    try:
        # Download if requested
        if args.download:
            import asyncio
            success = asyncio.run(download_gtfs_static(
                settings.gtfs_static_url,
                args.zip_path
            ))
            if not success:
                sys.exit(1)

            # Extract the downloaded file
            if not extract_gtfs_zip(args.zip_path, gtfs_path):
                sys.exit(1)

        # Check if GTFS data exists
        if not gtfs_path.exists():
            logger.error(f"GTFS data directory not found: {gtfs_path}")
            logger.error("Use --download to download data or provide --gtfs-path")
            sys.exit(1)

        # Create database engine and session
        engine = create_engine(settings.database_url, echo=False)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        # Create tables if requested
        if args.create_tables:
            logger.info("Creating database tables...")
            Base.metadata.create_all(bind=engine)

        # Load GTFS data
        loader = GTFSStaticLoader(str(gtfs_path))

        with SessionLocal() as db:
            logger.info("Starting GTFS data load...")
            counts = loader.load_all(db)

            logger.info("Load completed!")
            logger.info("Summary:")
            total_records = 0
            for filename, count in counts.items():
                logger.info(f"  {filename}: {count:,} records")
                total_records += count

            logger.info(f"Total records loaded: {total_records:,}")

    except KeyboardInterrupt:
        logger.info("Load interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Load failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()