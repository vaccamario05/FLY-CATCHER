"""
Module: web/app.py
Sprint: 2
Purpose: Flask application factory for ADS-B Secure dashboard.

Sprint 2 additions: auth, RBAC, forensic log API.
Sprint 3: ML-enriched responses, audit export.
"""

import logging
import os

from flask import Flask, jsonify, redirect, render_template_string, url_for

logger = logging.getLogger(__name__)

_STATUS_COLOR = {
    "valid": "#00ff41",
    "suspicious": "#ff4444",
    "unverified": "#ffaa00",
    "invalid": "#555555",
}

_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>ADS-B Secure Dashboard</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    * { box-sizing: border-box; }
    body { font-family: monospace; background: #0a0a0a; color: #00ff41; margin: 0; padding: 1rem; }
    h1 { border-bottom: 1px solid #00ff41; padding-bottom: .4rem; margin: 0 0 .5rem; font-size: 1.2rem; }
    a { color: #00ff41; }
    .top-bar { display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:.5rem; }
    .nav a { margin-left: .8rem; color: #aaa; text-decoration: none; font-size:.85em; }
    .nav a:hover { color: #00ff41; }
    .stats { font-size:.8em; color:#aaa; margin:.3rem 0; }
    #map { width:100%; height:400px; background:#111; border:1px solid #1a1a1a; margin:.5rem 0; border-radius:4px; }
    table { border-collapse: collapse; width: 100%; margin-top: .5rem; }
    th, td { border: 1px solid #1a1a1a; padding: .3rem .6rem; text-align: left; font-size: .8em; }
    th { background:#111; color:#aaa; }
    .valid   { color: #00ff41; }
    .suspicious { color: #ff4444; font-weight: bold; }
    .unverified { color: #ffaa00; }
    .invalid { color: #555; }
    .badge { padding: .1rem .3rem; border-radius: 3px; font-size:.75em; }
  </style>
</head>
<body>
  <div class="top-bar">
    <h1>&#9992; ADS-B Secure</h1>
    <nav class="nav">
      {% if role == 'analyst' %}
        <a href="/api/audit/logs">Audit Logs</a>
        <a href="/api/audit/verify">Chain Verify</a>
        <a href="/api/export/csv">Export CSV</a>
      {% endif %}
      <a href="/logout">Logout ({{ username }})</a>
    </nav>
  </div>
  <div class="stats">
    Traces: <strong>{{ traces|length }}</strong> &nbsp;|&nbsp;
    <span style="color:#ff4444">Suspicious: <strong>{{ suspicious }}</strong></span> &nbsp;|&nbsp;
    Auto-refresh: 5s &nbsp;|&nbsp; Role: <em>{{ role }}</em>
  </div>

  <!-- Leaflet map -->
  <div id="map"></div>

  <!-- Trace table -->
  <table>
    <tr>
      <th>ICAO</th><th>Flight</th><th>Status</th>
      <th>Lat</th><th>Lon</th><th>Alt (ft)</th>
      <th>Speed (kt)</th><th>Track&deg;</th><th>Anomaly</th><th>Reason</th>
    </tr>
    {% for t in traces %}
    <tr>
      <td><a href="/api/aircraft/{{ t.hex }}">{{ t.hex }}</a></td>
      <td>{{ t.flight or '—' }}</td>
      <td class="{{ t.status }}"><span class="badge">{{ t.status.upper() }}</span></td>
      <td>{{ '%.4f'|format(t.lat) if t.lat is not none else '—' }}</td>
      <td>{{ '%.4f'|format(t.lon) if t.lon is not none else '—' }}</td>
      <td>{{ t.altitude|int if t.altitude is not none else '—' }}</td>
      <td>{{ t.speed|int if t.speed is not none else '—' }}</td>
      <td>{{ t.track|int if t.track is not none else '—' }}</td>
      <td>{{ '%.2f'|format(t.anomaly_score) if t.anomaly_score is not none else '—' }}</td>
      <td style="font-size:.75em;color:#888">
        {{ (t.structural_reasons + ([t.anomaly_reason] if t.anomaly_reason else []))|join(', ') or '—' }}
      </td>
    </tr>
    {% endfor %}
  </table>

  <script>
    // Leaflet map — dark tiles
    var map = L.map('map', {zoomControl: true}).setView([30, 0], 2);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OpenStreetMap &copy; CARTO',
      maxZoom: 18
    }).addTo(map);

    var statusColor = {valid:'#00ff41', suspicious:'#ff4444', unverified:'#ffaa00', invalid:'#555'};
    var markers = {};

    function refreshTraces() {
      fetch('/api/traces')
        .then(r => r.json())
        .then(traces => {
          var seen = new Set();
          traces.forEach(t => {
            if (t.lat == null || t.lon == null) return;
            seen.add(t.hex);
            var color = statusColor[t.status] || '#888';
            var label = (t.flight || t.hex).trim();
            var popup = '<b>' + label + '</b><br/>'
              + 'Status: <span style="color:' + color + '">' + t.status.toUpperCase() + '</span><br/>'
              + 'Alt: ' + (t.altitude ? Math.round(t.altitude) + ' ft' : '—') + '<br/>'
              + 'Speed: ' + (t.speed ? Math.round(t.speed) + ' kt' : '—') + '<br/>'
              + (t.anomaly_score != null ? 'Anomaly: ' + t.anomaly_score.toFixed(2) + '<br/>' : '')
              + (t.anomaly_reason ? '<em>' + t.anomaly_reason + '</em>' : '');

            if (markers[t.hex]) {
              markers[t.hex].setLatLng([t.lat, t.lon])
                .setStyle({color: color, fillColor: color})
                .setPopupContent(popup);
            } else {
              markers[t.hex] = L.circleMarker([t.lat, t.lon], {
                radius: 6, color: color, fillColor: color,
                fillOpacity: 0.85, weight: 1.5
              }).bindPopup(popup).addTo(map);
            }
          });
          // Remove stale markers
          Object.keys(markers).forEach(hex => {
            if (!seen.has(hex)) { map.removeLayer(markers[hex]); delete markers[hex]; }
          });
        }).catch(() => {});
    }

    refreshTraces();
    setInterval(refreshTraces, 5000);
  </script>
</body>
</html>
"""


def create_app(trace_store=None, forensic_logger=None) -> Flask:
    """
    Flask application factory.

    :param trace_store: TraceStore shared with pipeline.
    :param forensic_logger: ForensicLogger instance for audit routes.
    """
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(32))

    if trace_store is None:
        from adsb_secure.trace_store import TraceStore
        trace_store = TraceStore()

    app.trace_store = trace_store
    app.forensic_logger = forensic_logger  # may be None in Sprint 1 mode

    # Register auth blueprint
    from web.auth import auth_bp
    app.register_blueprint(auth_bp)

    # ------------------------------------------------------------------ #
    # Public routes
    # ------------------------------------------------------------------ #

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "sprint": 2})

    # ------------------------------------------------------------------ #
    # Protected routes — require auth
    # ------------------------------------------------------------------ #

    from web.auth import require_auth, require_role, current_role
    from flask import session

    @app.get("/")
    @require_auth
    def dashboard():
        traces = app.trace_store.all_current()
        suspicious = sum(1 for t in traces if t.status.value == "suspicious")
        return render_template_string(
            _DASHBOARD_HTML,
            traces=traces,
            suspicious=suspicious,
            username=session.get("username", "?"),
            role=session.get("role", "operator"),
        )

    @app.get("/api/traces")
    @require_auth
    def api_traces():
        traces = app.trace_store.all_current()
        return jsonify([t.to_dict() for t in traces])

    @app.get("/api/aircraft/<icao>")
    @require_auth
    def api_aircraft_detail(icao: str):
        history = app.trace_store.get_history(icao.lower())
        if not history:
            return jsonify({"error": "not_found", "icao": icao}), 404
        return jsonify({
            "icao": icao.lower(),
            "count": len(history),
            "latest": history[-1].to_dict(),
            "history": [t.to_dict() for t in history],
        })

    # ------------------------------------------------------------------ #
    # Analyst-only routes
    # ------------------------------------------------------------------ #

    @app.get("/api/audit/logs")
    @require_role("analyst")
    def api_audit_logs():
        if not app.forensic_logger:
            return jsonify({"error": "forensic_logger_not_configured"}), 503
        event_type = request.args.get("event_type")
        severity = request.args.get("severity")
        icao = request.args.get("icao")
        limit = min(int(request.args.get("limit", 100)), 1000)
        events = app.forensic_logger.read_events(
            event_type=event_type, severity=severity, icao=icao, limit=limit
        )
        return jsonify({"count": len(events), "events": events})

    @app.get("/api/audit/verify")
    @require_role("analyst")
    def api_audit_verify():
        if not app.forensic_logger:
            return jsonify({"error": "forensic_logger_not_configured"}), 503
        ok, broken_at = app.forensic_logger.verify_chain()
        return jsonify({"chain_intact": ok, "broken_at_line": broken_at})

    @app.get("/api/export/csv")
    @require_role("analyst")
    def api_export_csv():
        if not app.forensic_logger:
            return jsonify({"error": "forensic_logger_not_configured"}), 503
        import csv
        import io
        from flask import Response
        events = app.forensic_logger.read_events(limit=10000)
        buf = io.StringIO()
        if events:
            writer = csv.DictWriter(buf, fieldnames=events[0].keys())
            writer.writeheader()
            writer.writerows(events)
        return Response(
            buf.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit_log.csv"},
        )

    # Need request in scope for audit routes
    from flask import request

    return app
