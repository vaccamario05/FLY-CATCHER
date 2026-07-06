"""
Guards against JS syntax errors silently breaking the dashboard.

A syntax error anywhere in a <script> block aborts the whole script with
no visible error except in the browser console — Leaflet map init,
refreshTraces(), search/filter all stop working with zero server-side
signal. This happened once from a Python-string-escaping bug (\\' consumed
by Python before it ever reached the browser). Node's `--check` catches
these without needing a real browser.
"""

import re
import shutil
import subprocess
import tempfile

import pytest

from web.app import create_app
from adsb_secure.trace_store import TraceStore
from adsb_secure.normalizer import AirCraftData, TraceStatus

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def _extract_scripts(html: str) -> list[str]:
    return re.findall(r"<script>(.*?)</script>", html, re.S)


def _assert_valid_js(script: str):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write(script)
        path = f.name
    result = subprocess.run(["node", "--check", path], capture_output=True, text=True)
    assert result.returncode == 0, f"JS syntax error:\n{result.stderr}"


@pytest.fixture
def store_with_trace():
    store = TraceStore()
    ac = AirCraftData(
        hex="abc123", squawk="7700", flight="TEST1", lat=45.0, lon=9.0,
        seen_pos=1.0, altitude=35000, vert_rate=500, track=90.0, rssi=-20,
        speed=450, messages=42, seen=1.0, mlat=None,
    )
    ac.status = TraceStatus.SUSPICIOUS
    ac.hmac_valid = False
    ac.replay_detected = True
    ac.anomaly_reason = "speed_discrepancy=520kt"
    store.update(ac)
    return store


def test_dashboard_script_is_valid_js(store_with_trace):
    app = create_app(trace_store=store_with_trace)
    app.config["TESTING"] = True
    c = app.test_client()
    c.post("/login", data={"username": "operator", "password": "operator123"})
    html = c.get("/").get_data(as_text=True)

    scripts = _extract_scripts(html)
    assert scripts, "no <script> block found in dashboard HTML"
    for script in scripts:
        _assert_valid_js(script)


def test_dashboard_script_valid_for_analyst_with_alerts(store_with_trace):
    """Analyst role renders the alert panel + chain banner — extra JS paths."""
    app = create_app(trace_store=store_with_trace)
    app.config["TESTING"] = True
    c = app.test_client()
    c.post("/login", data={"username": "analyst", "password": "analyst123"})
    html = c.get("/").get_data(as_text=True)

    for script in _extract_scripts(html):
        _assert_valid_js(script)


def test_analyst_events_script_is_valid_js():
    app = create_app(trace_store=TraceStore())
    app.config["TESTING"] = True
    c = app.test_client()
    c.post("/login", data={"username": "analyst", "password": "analyst123"})
    html = c.get("/analyst/events").get_data(as_text=True)

    scripts = _extract_scripts(html)
    assert scripts, "no <script> block found in analyst events HTML"
    for script in scripts:
        _assert_valid_js(script)
