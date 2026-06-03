"""
Module: web/app.py
Sprint: 1
Purpose: Flask application factory for ADS-B Secure dashboard.

Sprint 1: /health, /api/traces, /api/aircraft/<icao>, dashboard placeholder.
Sprint 2: auth, RBAC, forensic log API.
Sprint 3: ML-enriched responses, audit export.
"""

import logging
import os

from flask import Flask, jsonify, render_template_string

logger = logging.getLogger(__name__)

_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>ADS-B Secure Dashboard</title>
  <meta http-equiv="refresh" content="5">
  <style>
    body { font-family: monospace; background: #0a0a0a; color: #00ff41; margin: 2rem; }
    h1 { border-bottom: 1px solid #00ff41; padding-bottom: .5rem; }
    table { border-collapse: collapse; width: 100%; margin-top: 1rem; }
    th, td { border: 1px solid #1a1a1a; padding: .4rem .8rem; text-align: left; }
    .valid { color: #00ff41; }
    .suspicious { color: #ff4444; }
    .unverified { color: #ffaa00; }
    .invalid { color: #888; }
    .badge { padding: .1rem .4rem; border-radius: 3px; font-size: .8em; }
  </style>
</head>
<body>
  <h1>ADS-B Secure &mdash; Sprint 1 Dashboard</h1>
  <p>Traces: <strong>{{ traces|length }}</strong> &nbsp;|&nbsp;
     Auto-refresh: 5s &nbsp;|&nbsp;
     <em>RBAC and auth coming in Sprint 2</em></p>
  <table>
    <tr>
      <th>ICAO</th><th>Flight</th><th>Status</th>
      <th>Lat</th><th>Lon</th><th>Alt (ft)</th>
      <th>Speed (kt)</th><th>Track</th><th>Reasons</th>
    </tr>
    {% for t in traces %}
    <tr>
      <td><a href="/api/aircraft/{{ t.hex }}" style="color:inherit">{{ t.hex }}</a></td>
      <td>{{ t.flight or '—' }}</td>
      <td class="{{ t.status }}">
        <span class="badge">{{ t.status.upper() }}</span>
      </td>
      <td>{{ t.lat }}</td>
      <td>{{ t.lon }}</td>
      <td>{{ t.altitude }}</td>
      <td>{{ t.speed }}</td>
      <td>{{ t.track }}</td>
      <td style="font-size:.75em;color:#888">{{ t.structural_reasons|join(', ') or '—' }}</td>
    </tr>
    {% endfor %}
  </table>
</body>
</html>
"""


def create_app(trace_store=None) -> Flask:
    """
    Flask application factory.

    :param trace_store: TraceStore instance shared with the pipeline.
                        If None, returns empty data (useful for testing).
    """
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(32))

    if trace_store is None:
        from adsb_secure.trace_store import TraceStore
        trace_store = TraceStore()

    # Attach store to app for access in routes
    app.trace_store = trace_store

    # ------------------------------------------------------------------ #
    # Routes
    # ------------------------------------------------------------------ #

    @app.get("/health")
    def health():
        """Liveness probe."""
        return jsonify({"status": "ok", "sprint": 1})

    @app.get("/")
    def dashboard():
        """Dashboard placeholder — shows current traces."""
        traces = app.trace_store.all_current()
        return render_template_string(_DASHBOARD_HTML, traces=traces)

    @app.get("/api/traces")
    def api_traces():
        """Return all current traces as JSON."""
        traces = app.trace_store.all_current()
        return jsonify([t.to_dict() for t in traces])

    @app.get("/api/aircraft/<icao>")
    def api_aircraft_detail(icao: str):
        """Return full history for a single ICAO."""
        history = app.trace_store.get_history(icao.lower())
        if not history:
            return jsonify({"error": "not_found", "icao": icao}), 404
        return jsonify({
            "icao": icao.lower(),
            "count": len(history),
            "latest": history[-1].to_dict(),
            "history": [t.to_dict() for t in history],
        })

    return app
