"""
Module: normalizer.py
Sprint: 1
Purpose: AirCraftData dataclass with security fields + TraceStatus enum.

Handles field name variants:
  - Fly-catcher / dump1090: altitude, speed, vert_rate
  - Sample JSON / notebook: alt_baro, gs, baro_rate
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TraceStatus(str, Enum):
    VALID = "valid"
    SUSPICIOUS = "suspicious"
    UNVERIFIED = "unverified"
    INVALID = "invalid"


@dataclass
class AirCraftData:
    # --- Core ADS-B fields ---
    hex: Optional[str]                  # ICAO 24-bit address
    squawk: Optional[str]
    flight: Optional[str]               # callsign
    lat: Optional[float]
    lon: Optional[float]
    seen_pos: Optional[float]           # seconds since last position update
    altitude: Optional[float]           # feet (alt_baro or altitude)
    vert_rate: Optional[float]          # feet/min (baro_rate or vert_rate)
    track: Optional[float]              # degrees 0-360
    rssi: Optional[float]               # dBFS
    speed: Optional[float]              # knots (gs or speed)
    messages: Optional[int]
    seen: Optional[float]               # seconds since last message
    mlat: Optional[list]

    # --- Security fields (Sprint 1+) ---
    status: TraceStatus = TraceStatus.UNVERIFIED
    structural_valid: bool = True
    structural_reasons: list = field(default_factory=list)
    hmac_valid: Optional[bool] = None   # Sprint 2
    replay_detected: bool = False       # Sprint 2
    anomaly_score: Optional[float] = None    # Sprint 3
    anomaly_reason: Optional[str] = None     # Sprint 3
    received_at: float = field(default_factory=time.time)

    def __hash__(self):
        return hash(self.hex)

    def __eq__(self, other):
        if not isinstance(other, AirCraftData):
            return False
        return self.hex == other.hex

    def to_dict(self) -> dict:
        return {
            "hex": self.hex,
            "squawk": self.squawk,
            "flight": self.flight.strip() if self.flight else None,
            "lat": self.lat,
            "lon": self.lon,
            "altitude": self.altitude,
            "speed": self.speed,
            "track": self.track,
            "vert_rate": self.vert_rate,
            "rssi": self.rssi,
            "messages": self.messages,
            "seen": self.seen,
            "seen_pos": self.seen_pos,
            "status": self.status.value,
            "structural_valid": self.structural_valid,
            "structural_reasons": self.structural_reasons,
            "hmac_valid": self.hmac_valid,
            "replay_detected": self.replay_detected,
            "anomaly_score": self.anomaly_score,
            "anomaly_reason": self.anomaly_reason,
            "received_at": self.received_at,
        }


def build_from_dict(raw: dict) -> AirCraftData:
    """
    Build AirCraftData from a raw dump1090 or sample JSON dict.
    Handles both field name variants.
    """
    altitude = raw.get("altitude") or raw.get("alt_baro")
    speed = raw.get("speed") or raw.get("gs")
    vert_rate = raw.get("vert_rate") or raw.get("baro_rate")

    return AirCraftData(
        hex=raw.get("hex"),
        squawk=raw.get("squawk"),
        flight=raw.get("flight"),
        lat=_safe_float(raw.get("lat")),
        lon=_safe_float(raw.get("lon")),
        seen_pos=_safe_float(raw.get("seen_pos")),
        altitude=_safe_float(altitude),
        vert_rate=_safe_float(vert_rate),
        track=_safe_float(raw.get("track")),
        rssi=_safe_float(raw.get("rssi")),
        speed=_safe_float(speed),
        messages=_safe_int(raw.get("messages")),
        seen=_safe_float(raw.get("seen")),
        mlat=raw.get("mlat"),
    )


def _safe_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _safe_int(v) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
