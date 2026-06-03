"""Tests for security/rate_limiter.py."""

import time
from security.rate_limiter import TokenBucketRateLimiter


def test_allows_under_limit():
    limiter = TokenBucketRateLimiter(pps=100, burst=100)
    for _ in range(50):
        assert limiter.allow() is True


def test_drops_over_burst():
    limiter = TokenBucketRateLimiter(pps=10, burst=10)
    results = [limiter.allow() for _ in range(20)]
    # First 10 allowed, rest dropped
    assert results[:10] == [True] * 10
    assert False in results[10:]


def test_stats_track_allowed_and_dropped():
    limiter = TokenBucketRateLimiter(pps=5, burst=5)
    for _ in range(10):
        limiter.allow()
    stats = limiter.stats
    assert stats["allowed"] == 5
    assert stats["dropped"] == 5


def test_reset_restores_full_bucket():
    limiter = TokenBucketRateLimiter(pps=5, burst=5)
    for _ in range(5):
        limiter.allow()
    limiter.reset()
    assert limiter.allow() is True


def test_refills_over_time():
    limiter = TokenBucketRateLimiter(pps=100, burst=10)
    # Drain bucket
    for _ in range(10):
        limiter.allow()
    # Wait for refill
    time.sleep(0.15)
    assert limiter.allow() is True


def test_pps_limit_in_stats():
    limiter = TokenBucketRateLimiter(pps=50)
    assert limiter.stats["pps_limit"] == 50
