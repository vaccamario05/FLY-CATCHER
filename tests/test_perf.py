"""
Performance smoke tests — PB13/RNF1 (quasi real-time dashboard, contained latency).

Not a load-testing harness: bounds the per-packet security pipeline latency
and confirms the rate limiter drops overflow instead of queuing/blocking,
so a burst degrades gracefully instead of growing unbounded latency.
"""

import time
import statistics

import pytest

from security.validator import StructuralValidator
from security.hmac_validator import HMACValidator
from security.replay_detector import ReplayDetector
from security.rate_limiter import TokenBucketRateLimiter
from security.classifier import classify

# Generous ceiling for a PoC on dev hardware — CI/dev machines vary.
# Well above real per-packet cost (sub-millisecond) but catches real regressions.
_MAX_P95_MS = 20.0
_MAX_MEAN_MS = 10.0


def _sample_packet(i: int) -> dict:
    return {
        "hex": f"{i:06x}",
        "flight": f"TST{i % 1000:04d}",
        "alt_baro": 30000 + (i % 500),
        "gs": 420.0 + (i % 50),
        "track": float(i % 360),
        "baro_rate": 0,
        "lat": 45.0 + (i % 100) * 0.001,
        "lon": 9.0 + (i % 100) * 0.001,
        "seen_pos": 1.0,
        "seen": 0.5,
        "messages": 100,
        "rssi": -20.0,
    }


def test_pipeline_latency_bounded():
    """Structural + HMAC + replay + classify chain stays fast per packet."""
    validator = StructuralValidator()
    hmac_validator = HMACValidator()
    replay_detector = ReplayDetector(check_stale=False)

    latencies_ms = []
    n = 500
    for i in range(n):
        raw = _sample_packet(i)
        start = time.perf_counter()

        aircraft = validator.validate(raw)
        aircraft = hmac_validator.validate(aircraft, None)
        aircraft = replay_detector.check(aircraft)
        aircraft = classify(aircraft)

        latencies_ms.append((time.perf_counter() - start) * 1000)

    mean_ms = statistics.mean(latencies_ms)
    p95_ms = statistics.quantiles(latencies_ms, n=20)[18]  # 95th percentile

    assert mean_ms < _MAX_MEAN_MS, f"mean latency {mean_ms:.3f}ms exceeds {_MAX_MEAN_MS}ms budget"
    assert p95_ms < _MAX_P95_MS, f"p95 latency {p95_ms:.3f}ms exceeds {_MAX_P95_MS}ms budget"


def test_rate_limiter_sheds_load_without_blocking():
    """
    Burst beyond capacity must be dropped (not queued) — pipeline never stalls
    waiting for tokens, so latency stays bounded under flood (MC4/PB9/PB13).
    """
    limiter = TokenBucketRateLimiter(pps=100, burst=100)

    accepted = dropped = 0
    start = time.perf_counter()
    for _ in range(1000):
        if limiter.allow():
            accepted += 1
        else:
            dropped += 1
    elapsed = time.perf_counter() - start

    # allow() must never block — 1000 calls should be near-instant
    assert elapsed < 0.5, f"allow() blocked/slowed under burst: {elapsed:.3f}s for 1000 calls"
    # Burst capacity respected: no more than burst accepted in a tight loop
    assert accepted <= limiter.burst + 5  # small tolerance for refill during the loop
    assert dropped > 0, "expected overflow packets to be shed, none were dropped"


def test_no_packet_loss_within_capacity():
    """Traffic within configured pps/burst must not be dropped (PB13: minimize loss)."""
    limiter = TokenBucketRateLimiter(pps=100, burst=200)

    dropped = 0
    for _ in range(200):
        if not limiter.allow():
            dropped += 1

    assert dropped == 0, f"{dropped} packets dropped within burst capacity — unexpected loss"
