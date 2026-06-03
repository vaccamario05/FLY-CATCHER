"""
Module: trace_store.py
Sprint: 1
Purpose: In-memory store of AirCraftData traces keyed by ICAO hex.

Maintains a bounded history per aircraft for feature extraction (Sprint 3).
Thread-safe via simple lock for future concurrent access.
"""

import threading
from collections import deque
from typing import Optional

from adsb_secure.normalizer import AirCraftData

_DEFAULT_HISTORY = 20   # max messages kept per ICAO


class TraceStore:
    """
    dict[icao_hex -> deque[AirCraftData]]

    Usage:
        store = TraceStore()
        store.update(aircraft)
        history = store.get_history("3c4b12")
        all_current = store.all_current()
    """

    def __init__(self, max_history: int = _DEFAULT_HISTORY):
        self._store: dict[str, deque[AirCraftData]] = {}
        self._max_history = max_history
        self._lock = threading.Lock()

    def update(self, aircraft: AirCraftData) -> None:
        """Add or update a trace. Skips records with no ICAO."""
        if not aircraft.hex:
            return
        with self._lock:
            if aircraft.hex not in self._store:
                self._store[aircraft.hex] = deque(maxlen=self._max_history)
            self._store[aircraft.hex].append(aircraft)

    def get_history(self, icao: str) -> list[AirCraftData]:
        """Return full history for an ICAO (oldest first)."""
        with self._lock:
            return list(self._store.get(icao, []))

    def get_latest(self, icao: str) -> Optional[AirCraftData]:
        """Return most recent record for an ICAO, or None."""
        with self._lock:
            dq = self._store.get(icao)
            return dq[-1] if dq else None

    def all_current(self) -> list[AirCraftData]:
        """Return latest record for every tracked ICAO."""
        with self._lock:
            return [dq[-1] for dq in self._store.values() if dq]

    def remove(self, icao: str) -> None:
        with self._lock:
            self._store.pop(icao, None)

    def icao_set(self) -> set[str]:
        with self._lock:
            return set(self._store.keys())

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)
