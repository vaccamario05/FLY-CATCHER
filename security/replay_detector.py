"""
Module: replay_detector.py
Sprint: 2
Purpose: Detect replay attacks via timestamp window and bounded deduplication.

A packet is a replay if:
  - its timestamp is older than now - WINDOW_SECONDS, OR
  - an identical (icao, seen, lat, lon) tuple was seen within the window.

Dedup set is bounded to prevent memory exhaustion.
"""

import logging
import os
import time
from collections import deque
from typing import Optional

from adsb_secure.normalizer import AirCraftData, TraceStatus

logger = logging.getLogger(__name__)

_DEFAULT_WINDOW = float(os.environ.get("HMAC_WINDOW_SECONDS", "30"))
_MAX_DEDUP = 10_000  # max entries in dedup set


def _make_key(aircraft: AirCraftData) -> Optional[tuple]:
    """Fingerprint for deduplication. Returns None if insufficient data."""
    if not aircraft.hex:
        return None
    return (
        aircraft.hex,
        aircraft.seen,
        aircraft.lat,
        aircraft.lon,
    )


class ReplayDetector:
    """
    Stateful replay detector. One instance per pipeline run.

    Usage:
        detector = ReplayDetector()
        aircraft = detector.check(aircraft)
        if aircraft.replay_detected:
            # handle
    """

    def __init__(self, window_seconds: float = _DEFAULT_WINDOW):
        self.window = window_seconds
        # bounded set: store (key, seen_at) pairs
        self._seen: deque = deque(maxlen=_MAX_DEDUP)
        self._seen_set: set = set()

    def check(self, aircraft: AirCraftData) -> AirCraftData:
        """
        Check aircraft for replay. Sets replay_detected=True and status=SUSPICIOUS
        if detected. Never raises.
        """
        now = time.time()

        # Timestamp check: packet must be fresh
        if aircraft.seen is not None:
            packet_age = now - aircraft.received_at
            # seen = seconds since last message; if seen > window, packet is stale
            if aircraft.seen > self.window:
                aircraft.replay_detected = True
                aircraft.status = TraceStatus.SUSPICIOUS
                logger.info(
                    "Replay detected (stale) hex=%s seen=%.1fs window=%.1fs",
                    aircraft.hex, aircraft.seen, self.window,
                )
                return aircraft

        # Deduplication check
        key = _make_key(aircraft)
        if key is not None:
            if key in self._seen_set:
                aircraft.replay_detected = True
                aircraft.status = TraceStatus.SUSPICIOUS
                logger.info("Replay detected (duplicate) hex=%s", aircraft.hex)
                return aircraft

            # Register new key; evict oldest if at capacity
            if len(self._seen_set) >= _MAX_DEDUP:
                oldest_key, _ = self._seen.popleft()
                self._seen_set.discard(oldest_key)

            self._seen.append((key, now))
            self._seen_set.add(key)

        aircraft.replay_detected = False
        return aircraft

    def clear(self) -> None:
        """Reset state (useful between test runs)."""
        self._seen.clear()
        self._seen_set.clear()
