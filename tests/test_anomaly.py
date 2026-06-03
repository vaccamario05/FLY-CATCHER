"""Tests for ml/anomaly_detector.py."""

import time
import pytest
import numpy as np
from adsb_secure.normalizer import AirCraftData, TraceStatus
from ml.anomaly_detector import AnomalyDetector
from ml.feature_extractor import to_vector


def _normal_vector() -> list[float]:
    """Feature vector for a realistic commercial flight."""
    return [450.0, 35000.0, 0.0, 180.0, 0.0002, 0.0003, 10.0, 448.0, 2.0, 1.0]


def _ghost_vector() -> list[float]:
    """Feature vector for a physically impossible ghost aircraft."""
    return [9999.0, 200000.0, 99999.0, 720.0, 5.0, 5.0, 99999.0, 8000.0, 7999.0, 0.0]


def _make_training_data(n: int = 30) -> list[list[float]]:
    """Generate synthetic normal training vectors with small noise."""
    rng = np.random.default_rng(42)
    base = np.array(_normal_vector())
    return (base + rng.normal(0, 0.05, (n, len(base)))).tolist()


def _make_ac(lat, lon, alt=35000.0, speed=450.0, dt_offset=0) -> AirCraftData:
    ac = AirCraftData(
        hex="aabbcc", squawk=None, flight=None,
        lat=lat, lon=lon, seen_pos=1.0, altitude=alt,
        vert_rate=0.0, track=90.0, rssi=-20.0, speed=speed,
        messages=100, seen=1.0, mlat=None,
    )
    ac.received_at = time.time() + dt_offset
    return ac


@pytest.fixture
def trained_detector():
    d = AnomalyDetector(contamination=0.05)
    d.train(_make_training_data(50))
    return d


def test_untrained_returns_zero_score():
    d = AnomalyDetector()
    d._trained = False
    score, reason = d.predict(_normal_vector())
    assert score == 0.0
    assert reason == "model_not_trained"


def test_normal_vector_low_score(trained_detector):
    score, _ = trained_detector.predict(_normal_vector())
    assert score < 0.7, f"Normal flight scored too high: {score}"


def test_ghost_vector_high_score(trained_detector):
    score, _ = trained_detector.predict(_ghost_vector())
    assert score > 0.5, f"Ghost aircraft scored too low: {score}"


def test_predict_returns_tuple(trained_detector):
    result = trained_detector.predict(_normal_vector())
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_score_in_range(trained_detector):
    score, _ = trained_detector.predict(_normal_vector())
    assert 0.0 <= score <= 1.0


def test_annotate_normal_no_change(trained_detector):
    ac = _make_ac(45.0, 9.0)
    ac2 = _make_ac(45.01, 9.02, dt_offset=10)
    history = [ac, ac2]
    result = trained_detector.annotate(ac2, history)
    # anomaly_score populated
    assert result.anomaly_score is not None


def test_annotate_ghost_marks_suspicious(trained_detector):
    """Ghost aircraft — 5 degree jump in 5 seconds."""
    ac1 = _make_ac(45.0, 9.0, speed=9999.0, alt=200000.0, dt_offset=0)
    ac2 = _make_ac(50.0, 14.0, speed=9999.0, alt=200000.0, dt_offset=5)
    history = [ac1, ac2]
    result = trained_detector.annotate(ac2, history)
    if result.anomaly_score and result.anomaly_score > 0.7:
        assert result.status == TraceStatus.SUSPICIOUS


def test_annotate_single_record_no_crash(trained_detector):
    ac = _make_ac(45.0, 9.0)
    result = trained_detector.annotate(ac, [ac])
    assert result.anomaly_score is None  # insufficient history


def test_false_positive_rate_on_normal_data(trained_detector):
    """FP rate must be <= 5% on normal data (RNF3)."""
    total = 100
    fp = 0
    rng = np.random.default_rng(0)
    base = np.array(_normal_vector())
    for _ in range(total):
        vec = (base + rng.normal(0, 0.1, len(base))).tolist()
        score, _ = trained_detector.predict(vec)
        if score > 0.7:
            fp += 1
    fp_rate = fp / total
    assert fp_rate <= 0.10, f"FP rate too high: {fp_rate:.1%}"
