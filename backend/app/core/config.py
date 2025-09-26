"""
Configuration settings for the NYC Subway ETA service
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Environment
    environment: str = "development"
    debug: bool = True

    # Database
    database_url: str = "postgresql://postgres:password@postgres:5432/nyc_subway"
    database_url_test: str = "sqlite:///./test.db"

    # Redis
    redis_url: str = "redis://redis:6379/0"
    redis_ttl_seconds: int = 90

    # MTA GTFS-RT Feeds (Updated free endpoints)
    mta_feed_urls: List[str] = [
        "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",  # 1234567S
        "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace",  # ACEH
        "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm",  # BDFMFS
        "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g",  # G
        "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz",  # JZ
        "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw",  # NQRW
        "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l",  # L
        "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si"  # SIR (Staten Island)
    ]

    # GTFS Static
    gtfs_static_path: str = "./data/gtfs_static"
    gtfs_static_url: str = "https://transitfeeds.com/p/mta/79/latest/download"

    # Background tasks
    gtfs_rt_poll_interval_seconds: int = 45
    max_feed_age_seconds: int = 120

    # Transfer penalties (seconds)
    transfer_penalty_min: int = 180
    transfer_penalty_max: int = 300

    # API settings
    api_timeout_seconds: float = 10.0
    max_route_results: int = 5

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()