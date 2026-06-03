"""
Module: forensic_logger.py
Sprint: 2
Purpose: Append-only forensic log with SHA-256 hash chaining.

Each record includes hash of previous record — tampering breaks the chain.
Log written as JSONL (one JSON object per line) in append mode.

Log path: logs/security_events.jsonl (configurable via LOG_FILE env).
"""

import hashlib
import json
import logging
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_LOG = os.environ.get("LOG_FILE", "logs/security_events.jsonl")
_GENESIS_HASH = "0" * 64  # sentinel for first record


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventType(str, Enum):
    PACKET_ACCEPTED = "packet_accepted"
    PACKET_INVALID = "packet_invalid"
    HMAC_FAIL = "hmac_fail"
    REPLAY_DETECTED = "replay_detected"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    ANOMALY_DETECTED = "anomaly_detected"
    LOGIN_FAILED = "login_failed"
    LOGIN_SUCCESS = "login_success"
    LOG_CHAIN_BROKEN = "log_chain_broken"


@dataclass
class SecurityEvent:
    event_type: str
    severity: str
    icao: Optional[str] = None
    details: dict = field(default_factory=dict)
    # filled by ForensicLogger
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    prev_hash: str = ""
    hash: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "severity": self.severity,
            "icao": self.icao,
            "details": self.details,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
        }


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


class ForensicLogger:
    """
    Append-only forensic logger with SHA-256 hash chaining.

    Usage:
        flog = ForensicLogger()
        flog.log(SecurityEvent(EventType.REPLAY_DETECTED, Severity.HIGH, icao="3c4b12"))

        # Verify chain integrity
        ok, broken_at = flog.verify_chain()
    """

    def __init__(self, log_path: str = _DEFAULT_LOG):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._last_hash = self._read_last_hash()

    def _read_last_hash(self) -> str:
        if not self.log_path.exists():
            return _GENESIS_HASH
        try:
            last_line = ""
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        last_line = line
            if not last_line:
                return _GENESIS_HASH
            record = json.loads(last_line)
            return record.get("hash", _GENESIS_HASH)
        except Exception as e:
            logger.error("Cannot read last hash from log: %s", e)
            return _GENESIS_HASH

    def log(self, event: SecurityEvent) -> SecurityEvent:
        """Append event to log. Sets prev_hash and hash. Thread-safe."""
        with self._lock:
            event.prev_hash = self._last_hash

            # Compute hash over canonical record content (excluding hash field itself)
            content = json.dumps({
                "id": event.id,
                "timestamp": event.timestamp,
                "event_type": event.event_type,
                "severity": event.severity,
                "icao": event.icao,
                "details": event.details,
                "prev_hash": event.prev_hash,
            }, sort_keys=True, separators=(",", ":"))
            event.hash = _sha256(content)

            line = json.dumps(event.to_dict(), separators=(",", ":"))
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

            self._last_hash = event.hash
            logger.debug("Logged %s severity=%s icao=%s", event.event_type, event.severity, event.icao)

        return event

    def verify_chain(self) -> tuple[bool, Optional[int]]:
        """
        Verify SHA-256 chain integrity over all log records.
        Returns (True, None) if chain intact.
        Returns (False, line_number) at first broken link.
        """
        if not self.log_path.exists():
            return True, None

        prev_hash = _GENESIS_HASH
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line_num, raw in enumerate(f, start=1):
                    raw = raw.strip()
                    if not raw:
                        continue
                    record = json.loads(raw)

                    # Recompute expected hash
                    content = json.dumps({
                        "id": record["id"],
                        "timestamp": record["timestamp"],
                        "event_type": record["event_type"],
                        "severity": record["severity"],
                        "icao": record.get("icao"),
                        "details": record.get("details", {}),
                        "prev_hash": record["prev_hash"],
                    }, sort_keys=True, separators=(",", ":"))
                    expected = _sha256(content)

                    if record.get("prev_hash") != prev_hash:
                        logger.error("Chain broken at line %d: prev_hash mismatch", line_num)
                        return False, line_num
                    if record.get("hash") != expected:
                        logger.error("Chain broken at line %d: hash mismatch", line_num)
                        return False, line_num

                    prev_hash = record["hash"]
        except Exception as e:
            logger.error("Chain verification error: %s", e)
            return False, None

        return True, None

    def read_events(
        self,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        icao: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """Read and filter log events. Most recent first."""
        if not self.log_path.exists():
            return []
        results = []
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]
            for raw in reversed(lines):
                if len(results) >= limit:
                    break
                rec = json.loads(raw)
                if event_type and rec.get("event_type") != event_type:
                    continue
                if severity and rec.get("severity") != severity:
                    continue
                if icao and rec.get("icao") != icao:
                    continue
                results.append(rec)
        except Exception as e:
            logger.error("Error reading events: %s", e)
        return results
