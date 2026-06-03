"""
Module: acquisition.py
Sprint: 1
Purpose: Fetch raw ADS-B JSON from dump1090 HTTP API or simulator.

Returns raw dicts — no parsing or validation here.
"""

import json
import logging
import os
from urllib.request import urlopen, Request
from urllib.error import URLError
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_DEFAULT_URL = os.environ.get(
    "DUMP1090_URL", "http://localhost:8080/data/aircraft.json"
)


class DataIngestion:
    """
    Fetch raw aircraft records from dump1090 or a simulator source.

    Usage:
        ingestion = DataIngestion()
        for raw_dict in ingestion.fetch():
            ...
    """

    def __init__(self, url: str = _DEFAULT_URL, simulator=None):
        """
        :param url: dump1090 HTTP URL
        :param simulator: optional simulator object with a fetch() method.
                         If set, reads from simulator instead of HTTP.
        """
        self.url = url
        self.simulator = simulator

    def fetch(self) -> list[dict]:
        """
        Return list of raw aircraft dicts. Never raises.
        Returns empty list on failure.
        """
        if self.simulator is not None:
            return self._fetch_from_simulator()
        return self._fetch_from_http()

    @staticmethod
    def _validate_url(url: str) -> None:
        """Reject non-HTTP schemes to prevent file:// or custom scheme abuse."""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Disallowed URL scheme: {parsed.scheme!r}")

    def _fetch_from_http(self) -> list[dict]:
        try:
            self._validate_url(self.url)
            req = urlopen(Request(self.url), timeout=5)  # nosec B310
            raw = req.read()
            data = json.loads(raw.decode("utf-8"))
            records = data.get("aircraft", [])
            logger.debug("Fetched %d records from %s", len(records), self.url)
            return records
        except URLError as e:
            logger.warning("dump1090 unreachable (%s): %s", self.url, e)
            return []
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Malformed dump1090 response: %s", e)
            return []

    def _fetch_from_simulator(self) -> list[dict]:
        try:
            return list(self.simulator.fetch())
        except Exception as e:
            logger.error("Simulator fetch failed: %s", e)
            return []
