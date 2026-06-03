"""
Module: feature_extractor.py
Sprint: 3
Purpose: Extract cinematically meaningful features from ADS-B trace history.

Features used by Isolation Forest for anomaly detection.
All delta values derived from consecutive messages for the same ICAO.
"""

import math
import logging
from typing import Optional

from adsb_secure.normalizer import AirCraftData

logger = logging.getLogger(__name__)

# Maximum physical constraints for civil aviation (for normalisation context)
_MAX_SPEED_KT = 1500.0
_MAX_ALT_FT = 60000.0
_MAX_DELTA_ALT_FPM = 10000.0  # extreme climb/descent


def _haversine_nm(lat1, lon1, lat2, lon2) -> float:
    """Distance in nautical miles between two lat/lon points."""
    R = 3440.065  # Earth radius in nautical miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def extract(history: list[AirCraftData]) -> Optional[dict]:
    """
    Extract feature vector from an aircraft's message history.

    Requires at least 2 records with position data.
    Returns None if insufficient data.

    Features:
      speed_kt          — latest reported speed
      altitude_ft       — latest reported altitude
      vert_rate_fpm     — latest reported vertical rate
      track_deg         — latest reported track
      delta_lat         — lat change per second (last two messages)
      delta_lon         — lon change per second (last two seconds)
      delta_alt_fpm     — altitude change rate between messages
      computed_speed_kt — speed implied by position delta (physics check)
      speed_discrepancy — |reported_speed - computed_speed|
      seen_pos          — seconds since last position update
    """
    if len(history) < 2:
        return None

    # Use last two records
    prev = history[-2]
    curr = history[-1]

    # Need position on both
    if None in (curr.lat, curr.lon, prev.lat, prev.lon):
        return None

    # Time delta
    dt = curr.received_at - prev.received_at
    if dt <= 0:
        dt = 1.0  # avoid division by zero

    # Position deltas
    delta_lat = (curr.lat - prev.lat) / dt
    delta_lon = (curr.lon - prev.lon) / dt

    # Distance-based speed
    dist_nm = _haversine_nm(prev.lat, prev.lon, curr.lat, curr.lon)
    hours = dt / 3600.0
    computed_speed = dist_nm / hours if hours > 0 else 0.0

    # Altitude delta
    alt_curr = curr.altitude or 0.0
    alt_prev = prev.altitude or 0.0
    delta_alt = (alt_curr - alt_prev) / (dt / 60.0) if dt > 0 else 0.0

    # Speed discrepancy
    reported_speed = curr.speed or 0.0
    speed_disc = abs(reported_speed - computed_speed)

    features = {
        "speed_kt": reported_speed,
        "altitude_ft": curr.altitude or 0.0,
        "vert_rate_fpm": curr.vert_rate or 0.0,
        "track_deg": curr.track or 0.0,
        "delta_lat": delta_lat,
        "delta_lon": delta_lon,
        "delta_alt_fpm": delta_alt,
        "computed_speed_kt": computed_speed,
        "speed_discrepancy": speed_disc,
        "seen_pos": curr.seen_pos or 0.0,
    }
    return features


def to_vector(features: dict) -> list[float]:
    """Convert feature dict to ordered list for ML model."""
    order = [
        "speed_kt", "altitude_ft", "vert_rate_fpm", "track_deg",
        "delta_lat", "delta_lon", "delta_alt_fpm",
        "computed_speed_kt", "speed_discrepancy", "seen_pos",
    ]
    return [features.get(k, 0.0) for k in order]
