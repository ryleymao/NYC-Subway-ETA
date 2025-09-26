#!/usr/bin/env python3
"""
Script to build the station graph from GTFS static data
Usage: python scripts/build_graph.py
"""
import logging
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.core.graph import StationGraphBuilder

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    try:
        # Get settings
        settings = get_settings()

        # Create database engine and session
        engine = create_engine(settings.database_url, echo=False)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        # Build graph
        builder = StationGraphBuilder()

        with SessionLocal() as db:
            logger.info("Building station graph from GTFS data...")
            counts = builder.build_graph(db)

            logger.info("Graph building completed!")
            logger.info("Summary:")
            for key, count in counts.items():
                logger.info(f"  {key}: {count:,}")

            logger.info("Station graph saved to database and ready for routing!")

    except KeyboardInterrupt:
        logger.info("Graph building interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Graph building failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()