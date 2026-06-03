"""
Module: replay.py
Sprint: 1
Purpose: Replay ADS-B JSON files for development without SDR hardware.

Supports single-shot and loop modes. Used as simulator= argument to DataIngestion.

Usage:
    sim = JSONSimulator("notebook/samples/testing/sample.json")
    for raw in sim.fetch():
        ...

    # Loop mode (repeats endlessly):
    sim = JSONSimulator("...", loop=True)

CLI:
    python3 -m simulator.replay --file notebook/samples/testing/sample.json
"""

import json
import logging
import os
import time
from typing import Iterator

logger = logging.getLogger(__name__)

_DEFAULT_FILE = os.path.join(
    os.path.dirname(__file__),
    "..", "notebook", "samples", "testing", "sample.json"
)


class JSONSimulator:
    """
    Reads aircraft records from a JSON file (dump1090 format).

    The file must be a dict with key "aircraft": [...]
    Compatible with notebook/samples/ files.
    """

    def __init__(self, file_path: str = _DEFAULT_FILE, loop: bool = False):
        self.file_path = os.path.abspath(file_path)
        self.loop = loop
        self._records: list[dict] = []
        self._loaded = False

    def _load(self) -> None:
        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        aircraft = data.get("aircraft", [])
        if not isinstance(aircraft, list):
            raise ValueError(f"Expected 'aircraft' list in {self.file_path}")
        self._records = aircraft
        self._loaded = True
        logger.info("Simulator loaded %d records from %s", len(aircraft), self.file_path)

    def fetch(self) -> list[dict]:
        """
        Return all aircraft records from the file.
        If loop=True, reloads from disk each call (simulates continuous feed).
        """
        if not self._loaded or self.loop:
            self._load()
        return list(self._records)

    def __iter__(self) -> Iterator[dict]:
        yield from self.fetch()


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="ADS-B JSON replay simulator")
    parser.add_argument("--file", default=_DEFAULT_FILE, help="Path to aircraft.json")
    parser.add_argument("--loop", action="store_true", help="Repeat indefinitely")
    parser.add_argument("--interval", type=float, default=2.0, help="Seconds between iterations")
    args = parser.parse_args()

    sim = JSONSimulator(args.file, loop=args.loop)
    iteration = 0
    while True:
        records = sim.fetch()
        iteration += 1
        print(f"[iter {iteration}] {len(records)} aircraft")
        for r in records:
            print(f"  {r.get('hex','?')} | {r.get('flight','?').strip()} | "
                  f"lat={r.get('lat')} lon={r.get('lon')} alt={r.get('alt_baro', r.get('altitude'))}")
        if not args.loop:
            break
        time.sleep(args.interval)
