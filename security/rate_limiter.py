"""
Module: rate_limiter.py
Sprint: 2
Purpose: Token bucket rate limiter for ADS-B packet ingestion.

Prevents packet flooding / DoS on the pipeline.
Limit configurable via env RATE_LIMIT_PPS (packets per second).
"""

import logging
import os
import time
import threading

logger = logging.getLogger(__name__)

_DEFAULT_PPS = int(os.environ.get("RATE_LIMIT_PPS", "100"))


class TokenBucketRateLimiter:
    """
    Token bucket algorithm.
    Bucket fills at `pps` tokens/second up to `burst` maximum.
    Each packet consumes 1 token. Returns False when bucket empty.

    Usage:
        limiter = TokenBucketRateLimiter(pps=100)
        if limiter.allow():
            process(packet)
        else:
            drop(packet)  # flood detected
    """

    def __init__(self, pps: int = _DEFAULT_PPS, burst: int = None):
        self.pps = pps
        self.burst = burst or pps * 2
        self._tokens = float(self.burst)
        self._last = time.monotonic()
        self._lock = threading.Lock()
        self._dropped = 0
        self._allowed = 0

    def allow(self) -> bool:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last
            self._last = now

            # Refill tokens
            self._tokens = min(
                self.burst,
                self._tokens + elapsed * self.pps,
            )

            if self._tokens >= 1.0:
                self._tokens -= 1.0
                self._allowed += 1
                return True
            else:
                self._dropped += 1
                if self._dropped % 100 == 1:
                    logger.warning(
                        "Rate limit exceeded: %d packets dropped (total)",
                        self._dropped,
                    )
                return False

    @property
    def stats(self) -> dict:
        with self._lock:
            return {
                "allowed": self._allowed,
                "dropped": self._dropped,
                "tokens": round(self._tokens, 2),
                "pps_limit": self.pps,
            }

    def reset(self) -> None:
        with self._lock:
            self._tokens = float(self.burst)
            self._dropped = 0
            self._allowed = 0
            self._last = time.monotonic()
