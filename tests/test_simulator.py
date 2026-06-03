"""Tests for simulator/replay.py — JSONSimulator."""

import os
import json
import tempfile
import pytest
from simulator.replay import JSONSimulator

_SAMPLE_FILE = os.path.join(
    os.path.dirname(__file__),
    "..", "notebook", "samples", "testing", "sample.json"
)


def test_simulator_loads_sample():
    sim = JSONSimulator(_SAMPLE_FILE)
    records = sim.fetch()
    assert isinstance(records, list)
    assert len(records) > 0


def test_simulator_records_have_hex():
    sim = JSONSimulator(_SAMPLE_FILE)
    for r in sim.fetch():
        assert "hex" in r


def test_simulator_returns_list_of_dicts():
    sim = JSONSimulator(_SAMPLE_FILE)
    records = sim.fetch()
    assert all(isinstance(r, dict) for r in records)


def test_simulator_iterable():
    sim = JSONSimulator(_SAMPLE_FILE)
    count = sum(1 for _ in sim)
    assert count > 0


def test_simulator_custom_json():
    data = {"aircraft": [
        {"hex": "aabbcc", "lat": 10.0, "lon": 20.0, "alt_baro": 5000},
        {"hex": "112233", "lat": 11.0, "lon": 21.0, "alt_baro": 6000},
    ]}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name
    try:
        sim = JSONSimulator(path)
        records = sim.fetch()
        assert len(records) == 2
        assert records[0]["hex"] == "aabbcc"
    finally:
        os.unlink(path)


def test_simulator_loop_reloads():
    sim = JSONSimulator(_SAMPLE_FILE, loop=True)
    r1 = sim.fetch()
    r2 = sim.fetch()
    assert len(r1) == len(r2)


def test_simulator_missing_file():
    sim = JSONSimulator("/nonexistent/path/sample.json")
    with pytest.raises(FileNotFoundError):
        sim.fetch()


def test_simulator_invalid_json():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("NOT JSON")
        path = f.name
    try:
        sim = JSONSimulator(path)
        with pytest.raises(Exception):
            sim.fetch()
    finally:
        os.unlink(path)
