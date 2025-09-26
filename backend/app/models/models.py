"""
SQLAlchemy models for GTFS static data
"""
from typing import List
from datetime import date, time

from sqlalchemy import Column, Integer, String, Float, Date, Time, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.database import Base


class Agency(Base):
    """GTFS agencies table"""
    __tablename__ = "agencies"

    agency_id: Mapped[str] = mapped_column(String, primary_key=True)
    agency_name: Mapped[str] = mapped_column(String, nullable=False)
    agency_url: Mapped[str] = mapped_column(String, nullable=False)
    agency_timezone: Mapped[str] = mapped_column(String, nullable=False)
    agency_lang: Mapped[str] = mapped_column(String, nullable=True)


class Route(Base):
    """GTFS routes table"""
    __tablename__ = "routes"

    route_id: Mapped[str] = mapped_column(String, primary_key=True)
    agency_id: Mapped[str] = mapped_column(String, ForeignKey("agencies.agency_id"))
    route_short_name: Mapped[str] = mapped_column(String, nullable=True)
    route_long_name: Mapped[str] = mapped_column(String, nullable=True)
    route_desc: Mapped[str] = mapped_column(Text, nullable=True)
    route_type: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 for subway
    route_url: Mapped[str] = mapped_column(String, nullable=True)
    route_color: Mapped[str] = mapped_column(String, nullable=True)
    route_text_color: Mapped[str] = mapped_column(String, nullable=True)

    # Relationships
    trips: Mapped[List["Trip"]] = relationship("Trip", back_populates="route")


class Stop(Base):
    """GTFS stops table"""
    __tablename__ = "stops"

    stop_id: Mapped[str] = mapped_column(String, primary_key=True)
    stop_code: Mapped[str] = mapped_column(String, nullable=True)
    stop_name: Mapped[str] = mapped_column(String, nullable=False)
    stop_desc: Mapped[str] = mapped_column(Text, nullable=True)
    stop_lat: Mapped[float] = mapped_column(Float, nullable=False)
    stop_lon: Mapped[float] = mapped_column(Float, nullable=False)
    zone_id: Mapped[str] = mapped_column(String, nullable=True)
    stop_url: Mapped[str] = mapped_column(String, nullable=True)
    location_type: Mapped[int] = mapped_column(Integer, default=0)  # 0=stop, 1=station
    parent_station: Mapped[str] = mapped_column(String, nullable=True)

    # Relationships
    stop_times: Mapped[List["StopTime"]] = relationship("StopTime", back_populates="stop")


class Calendar(Base):
    """GTFS calendar table"""
    __tablename__ = "calendar"

    service_id: Mapped[str] = mapped_column(String, primary_key=True)
    monday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tuesday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    wednesday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    thursday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    friday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    saturday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    sunday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)


class CalendarDate(Base):
    """GTFS calendar_dates table"""
    __tablename__ = "calendar_dates"

    service_id: Mapped[str] = mapped_column(String, primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    exception_type: Mapped[int] = mapped_column(Integer, nullable=False)  # 1=added, 2=removed


class Trip(Base):
    """GTFS trips table"""
    __tablename__ = "trips"

    trip_id: Mapped[str] = mapped_column(String, primary_key=True)
    route_id: Mapped[str] = mapped_column(String, ForeignKey("routes.route_id"))
    service_id: Mapped[str] = mapped_column(String, nullable=False)
    trip_headsign: Mapped[str] = mapped_column(String, nullable=True)
    trip_short_name: Mapped[str] = mapped_column(String, nullable=True)
    direction_id: Mapped[int] = mapped_column(Integer, nullable=True)  # 0 or 1
    block_id: Mapped[str] = mapped_column(String, nullable=True)
    shape_id: Mapped[str] = mapped_column(String, nullable=True)

    # Relationships
    route: Mapped["Route"] = relationship("Route", back_populates="trips")
    stop_times: Mapped[List["StopTime"]] = relationship("StopTime", back_populates="trip", order_by="StopTime.stop_sequence")


class StopTime(Base):
    """GTFS stop_times table"""
    __tablename__ = "stop_times"

    trip_id: Mapped[str] = mapped_column(String, ForeignKey("trips.trip_id"), primary_key=True)
    arrival_time: Mapped[str] = mapped_column(String, nullable=True)  # HH:MM:SS format
    departure_time: Mapped[str] = mapped_column(String, nullable=True)  # HH:MM:SS format
    stop_id: Mapped[str] = mapped_column(String, ForeignKey("stops.stop_id"), primary_key=True)
    stop_sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    stop_headsign: Mapped[str] = mapped_column(String, nullable=True)
    pickup_type: Mapped[int] = mapped_column(Integer, default=0)
    drop_off_type: Mapped[int] = mapped_column(Integer, default=0)
    shape_dist_traveled: Mapped[float] = mapped_column(Float, nullable=True)

    # Relationships
    trip: Mapped["Trip"] = relationship("Trip", back_populates="stop_times")
    stop: Mapped["Stop"] = relationship("Stop", back_populates="stop_times")


class Transfer(Base):
    """GTFS transfers table"""
    __tablename__ = "transfers"

    from_stop_id: Mapped[str] = mapped_column(String, primary_key=True)
    to_stop_id: Mapped[str] = mapped_column(String, primary_key=True)
    transfer_type: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=recommended, 1=timed, 2=min_time, 3=not_possible
    min_transfer_time: Mapped[int] = mapped_column(Integer, nullable=True)  # seconds


class Shape(Base):
    """GTFS shapes table"""
    __tablename__ = "shapes"

    shape_id: Mapped[str] = mapped_column(String, primary_key=True)
    shape_pt_lat: Mapped[float] = mapped_column(Float, primary_key=True)
    shape_pt_lon: Mapped[float] = mapped_column(Float, primary_key=True)
    shape_pt_sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    shape_dist_traveled: Mapped[float] = mapped_column(Float, nullable=True)


# Custom tables for our service
class StationGraph(Base):
    """Pre-computed station graph for routing"""
    __tablename__ = "station_graph"

    from_stop_id: Mapped[str] = mapped_column(String, primary_key=True)
    to_stop_id: Mapped[str] = mapped_column(String, primary_key=True)
    route_id: Mapped[str] = mapped_column(String, primary_key=True)
    travel_time_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    is_transfer: Mapped[bool] = mapped_column(Boolean, default=False)
    transfer_penalty_seconds: Mapped[int] = mapped_column(Integer, default=0)