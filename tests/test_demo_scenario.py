"""Tests for demo/scenario.py — scripted demo aircraft covering every classification path."""

from demo.scenario import DemoScenarioSimulator, HMAC_TAMPER_ICAO
from security.validator import StructuralValidator
from security.replay_detector import ReplayDetector
from security.classifier import classify


class _FakeSim:
    def fetch(self):
        return []  # no real aircraft needed to test the injected ones


def test_injects_five_records_per_cycle():
    demo = DemoScenarioSimulator(_FakeSim())
    records = demo.fetch()
    assert len(records) == 5


def test_ghost01_fails_structural_validation():
    demo = DemoScenarioSimulator(_FakeSim())
    records = demo.fetch()
    validator = StructuralValidator()
    ac = validator.validate(next(r for r in records if r["hex"] == "GHOST01"))
    assert ac.structural_valid is False


def test_altitude_out_of_range_fails_structural_validation():
    demo = DemoScenarioSimulator(_FakeSim())
    records = demo.fetch()
    validator = StructuralValidator()
    ac = validator.validate(next(r for r in records if r["hex"] == "abc123"))
    assert ac.structural_valid is False
    assert any("altitude" in r for r in ac.structural_reasons)


def test_ghost02_position_alternates_between_cycles():
    demo = DemoScenarioSimulator(_FakeSim())
    r1 = next(r for r in demo.fetch() if r["hex"] == "def456")
    r2 = next(r for r in demo.fetch() if r["hex"] == "def456")
    assert (r1["lat"], r1["lon"]) != (r2["lat"], r2["lon"])


def test_replay1_identical_every_cycle_triggers_replay_detection():
    demo = DemoScenarioSimulator(_FakeSim())
    validator = StructuralValidator()
    rd = ReplayDetector(check_stale=False)

    for _ in range(2):
        raw = next(r for r in demo.fetch() if r["hex"] == "112233")
        ac = validator.validate(raw)
        ac = rd.check(ac)
        last = ac

    assert last.replay_detected is True
    assert classify(last).status.value == "suspicious"


def test_hmac_tamper_icao_is_structurally_valid():
    """The record targeted for HMAC tampering must itself pass structural
    validation — otherwise it would never reach the HMAC check at all."""
    demo = DemoScenarioSimulator(_FakeSim())
    records = demo.fetch()
    validator = StructuralValidator()
    ac = validator.validate(next(r for r in records if r["hex"] == HMAC_TAMPER_ICAO))
    assert ac.structural_valid is True


def test_real_records_pass_through_unchanged():
    class _RealSim:
        def fetch(self):
            return [{"hex": "aabbcc", "flight": "REAL1"}]

    demo = DemoScenarioSimulator(_RealSim())
    records = demo.fetch()
    assert {"hex": "aabbcc", "flight": "REAL1"} in records
    assert len(records) == 1 + 5
