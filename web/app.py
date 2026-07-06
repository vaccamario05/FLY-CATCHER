"""
Module: web/app.py
Sprint: 2
Purpose: Flask application factory for ADS-B Secure dashboard.

Sprint 2 additions: auth, RBAC, forensic log API.
Sprint 3: ML-enriched responses, audit export.
"""

import logging
import os
import time

from flask import Flask, jsonify, redirect, render_template_string, request, session, url_for

logger = logging.getLogger(__name__)

_STATUS_COLOR = {
    "valid": "#00ff41",
    "suspicious": "#ff4444",
    "unverified": "#ffaa00",
    "invalid": "#555555",
}

# Alert severity derived from trace status
_TRACE_SEVERITY = {"invalid": "high", "suspicious": "medium", "unverified": "low"}
_SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
_ALERT_MIN_SEVERITY = os.environ.get("ALERT_MIN_SEVERITY", "medium")

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
    /* Alert panel */
    .alert-panel { border: 1px solid #ff4444; background:#0d0000; padding:.5rem .8rem; margin:.4rem 0; border-radius:3px; }
    .alert-panel-title { color:#ff4444; font-size:.9em; font-weight:bold; margin:0 0 .4rem; }
    .alert-row { display:flex; align-items:baseline; gap:.5rem; padding:.2rem 0; border-bottom:1px solid #1a0000; font-size:.8em; }
    .alert-row:last-child { border-bottom:none; }
    .sev-high { background:#ff0000; color:#000; padding:.1rem .3rem; border-radius:3px; font-size:.7em; font-weight:bold; }
    .sev-medium { background:#ff8800; color:#000; padding:.1rem .3rem; border-radius:3px; font-size:.7em; font-weight:bold; }
    .chain-banner { display:none; background:#1a0000; border:1px solid #ff0000; color:#ff4444;
                    padding:.5rem .8rem; margin:.4rem 0; font-weight:bold; font-size:.85em; border-radius:3px; }
  </style>
</head>
<body>
  <div class="top-bar">
    <h1>&#9992; ADS-B Secure</h1>
    <nav class="nav">
      {% if role == 'analyst' %}
        <a href="/analyst/events">Events</a>
        <a href="/api/audit/logs">Audit API</a>
        <a href="/api/audit/verify">Chain Verify</a>
        <a href="/api/export/csv">Export CSV</a>
        <a href="/api/export/pdf">Export PDF</a>
      {% endif %}
      <a href="/logout">Logout ({{ username }} &mdash; {{ role }})</a>
    </nav>
  </div>

  {% if role == 'analyst' %}
  <div class="chain-banner" id="chain-banner"></div>
  {% endif %}

  <div class="stats">
    Traces: <strong>{{ traces|length }}</strong> &nbsp;|&nbsp;
    <span style="color:#ff4444">Suspicious: <strong>{{ suspicious }}</strong></span> &nbsp;|&nbsp;
    Auto-refresh: 5s &nbsp;|&nbsp; Role: <em>{{ role }}</em>
  </div>

  {% if alerts %}
  <div class="alert-panel">
    <div class="alert-panel-title">&#9888; ACTIVE ALERTS ({{ alerts|length }})</div>
    {% for a in alerts %}
    <div class="alert-row">
      <span class="sev-{{ a.severity }}">{{ a.severity.upper() }}</span>
      <a href="/api/aircraft/{{ a.icao }}">{{ a.icao }}</a>
      {% if a.flight %}<em>({{ a.flight }})</em>{% endif %}
      &mdash; {{ a.reasons|join(' &middot; ') or 'Anomaly detected' }}
      {% if a.anomaly_score is not none %}<small style="color:#888">[score: {{ '%.2f'|format(a.anomaly_score) }}]</small>{% endif %}
    </div>
    {% endfor %}
  </div>
  {% endif %}

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
          Object.keys(markers).forEach(hex => {
            if (!seen.has(hex)) { map.removeLayer(markers[hex]); delete markers[hex]; }
          });
        }).catch(() => {});
    }

    refreshTraces();
    setInterval(refreshTraces, 5000);

    {% if role == 'analyst' %}
    // UC2 EX1: chain integrity banner for analyst
    fetch('/api/audit/verify')
      .then(r => r.json())
      .then(d => {
        if (!d.chain_intact) {
          var b = document.getElementById('chain-banner');
          b.textContent = '⚠ CRITICAL: Log chain integrity broken at record ' + d.broken_at_line + ' — potential log tampering detected';
          b.style.display = 'block';
        }
      }).catch(() => {});
    {% endif %}
  </script>
</body>
</html>
"""

_ANALYST_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>ADS-B Secure — Security Events</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: monospace; background: #0a0a0a; color: #00ff41; margin: 0; padding: 1rem; }
    h1 { border-bottom: 1px solid #00ff41; padding-bottom: .4rem; margin: 0 0 .8rem; font-size: 1.2rem; }
    a { color: #00ff41; }
    .top-bar { display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:.5rem; margin-bottom:.8rem; }
    .nav a { margin-left: .8rem; color: #aaa; text-decoration: none; font-size:.85em; }
    .nav a:hover { color: #00ff41; }
    .filters { display:flex; gap:.6rem; flex-wrap:wrap; align-items:flex-end; margin-bottom:.8rem;
               padding:.6rem; border:1px solid #1a1a1a; background:#0d0d0d; border-radius:3px; }
    .filters label { color:#aaa; font-size:.75em; display:block; margin-bottom:.2rem; }
    .filters select, .filters input {
      background:#111; color:#00ff41; border:1px solid #333;
      padding:.3rem .5rem; font-family:monospace; font-size:.8em; }
    .filters button {
      background:#00ff41; color:#000; border:none; padding:.35rem .9rem;
      cursor:pointer; font-family:monospace; font-weight:bold; }
    .stats { font-size:.8em; color:#aaa; margin-bottom:.5rem; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #1a1a1a; padding: .3rem .6rem; text-align: left; font-size: .75em; }
    th { background:#111; color:#aaa; cursor:pointer; user-select:none; }
    th:hover { color:#00ff41; }
    .sev-low { color: #aaa; }
    .sev-medium { color: #ffaa00; }
    .sev-high { color: #ff4444; font-weight:bold; }
    .sev-critical { color: #ff0000; font-weight:bold; }
    .chain-ok { color:#00ff41; font-size:.8em; margin-bottom:.5rem; }
    .chain-broken { color:#ff4444; font-weight:bold; padding:.4rem .8rem; border:1px solid #ff0000;
                    background:#1a0000; margin-bottom:.8rem; border-radius:3px; }
    .details { max-width:280px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:#888; }
  </style>
</head>
<body>
  <div class="top-bar">
    <h1>&#128269; Security Events</h1>
    <nav class="nav">
      <a href="/">Dashboard</a>
      <a href="/api/export/csv">Export CSV</a>
      <a href="/api/export/pdf">Export PDF</a>
      <a href="/logout">Logout ({{ username }})</a>
    </nav>
  </div>

  <div id="chain-status"></div>

  <div class="filters">
    <div>
      <label>Event Type</label>
      <select id="f-type">
        <option value="">All</option>
        <option value="hmac_fail">HMAC Fail</option>
        <option value="replay_detected">Replay Detected</option>
        <option value="anomaly_detected">Anomaly Detected</option>
        <option value="packet_invalid">Packet Invalid</option>
        <option value="rate_limit_exceeded">Rate Limit Exceeded</option>
        <option value="login_failed">Login Failed</option>
        <option value="login_success">Login Success</option>
        <option value="audit_export">Audit Export</option>
        <option value="log_chain_broken">Chain Broken</option>
      </select>
    </div>
    <div>
      <label>Min Severity</label>
      <select id="f-severity">
        <option value="">All</option>
        <option value="low">Low</option>
        <option value="medium">Medium</option>
        <option value="high">High</option>
        <option value="critical">Critical</option>
      </select>
    </div>
    <div>
      <label>ICAO</label>
      <input id="f-icao" type="text" placeholder="e.g. 3c4b12" style="width:110px">
    </div>
    <div>
      <label>Sort by</label>
      <select id="f-sort">
        <option value="timestamp">Timestamp</option>
        <option value="severity">Severity</option>
        <option value="event_type">Event Type</option>
      </select>
    </div>
    <div>
      <label>Limit</label>
      <select id="f-limit">
        <option value="50">50</option>
        <option value="100" selected>100</option>
        <option value="500">500</option>
        <option value="1000">1000</option>
      </select>
    </div>
    <button onclick="loadEvents()">Apply</button>
  </div>

  <div class="stats" id="stats">Loading...</div>

  <table>
    <thead>
      <tr>
        <th onclick="sortBy('timestamp')">Timestamp &#8597;</th>
        <th onclick="sortBy('event_type')">Event Type &#8597;</th>
        <th onclick="sortBy('severity')">Severity &#8597;</th>
        <th>ICAO</th>
        <th>Details</th>
        <th style="color:#333">ID</th>
      </tr>
    </thead>
    <tbody id="events-body"></tbody>
  </table>

  <script>
    var allEvents = [];
    var sortField = 'timestamp';
    var sortAsc = false;

    function fmtTs(t) {
      return new Date(t * 1000).toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
    }

    var sevOrder = {low:0, medium:1, high:2, critical:3};

    function loadEvents() {
      var params = new URLSearchParams();
      var t = document.getElementById('f-type').value;
      var s = document.getElementById('f-severity').value;
      var i = document.getElementById('f-icao').value.trim();
      var l = document.getElementById('f-limit').value;
      sortField = document.getElementById('f-sort').value;
      sortAsc = false;
      if (t) params.set('event_type', t);
      if (s) params.set('severity', s);
      if (i) params.set('icao', i);
      params.set('limit', l);

      fetch('/api/audit/logs?' + params.toString())
        .then(r => r.json())
        .then(data => {
          allEvents = data.events || [];
          document.getElementById('stats').textContent =
            'Showing ' + allEvents.length + ' events';
          renderTable();
        })
        .catch(e => {
          document.getElementById('stats').textContent = 'Error: ' + e;
        });
    }

    function sortBy(field) {
      if (sortField === field) sortAsc = !sortAsc;
      else { sortField = field; sortAsc = false; }
      renderTable();
    }

    function renderTable() {
      var sorted = allEvents.slice().sort(function(a, b) {
        var va = a[sortField], vb = b[sortField];
        if (sortField === 'severity') { va = sevOrder[va] || 0; vb = sevOrder[vb] || 0; }
        if (va < vb) return sortAsc ? -1 : 1;
        if (va > vb) return sortAsc ? 1 : -1;
        return 0;
      });

      var rows = sorted.map(function(e) {
        var det = JSON.stringify(e.details || {});
        var detSafe = det.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');
        return '<tr>'
          + '<td>' + fmtTs(e.timestamp) + '</td>'
          + '<td>' + (e.event_type || '—') + '</td>'
          + '<td class="sev-' + (e.severity||'low') + '">' + (e.severity || '—').toUpperCase() + '</td>'
          + '<td>' + (e.icao || '—') + '</td>'
          + '<td class="details" title="' + detSafe + '">' + det + '</td>'
          + '<td style="color:#2a2a2a;font-size:.7em">' + (e.id || '').slice(0, 8) + '&hellip;</td>'
          + '</tr>';
      });
      document.getElementById('events-body').innerHTML = rows.join('');
    }

    function checkChain() {
      fetch('/api/audit/verify')
        .then(r => r.json())
        .then(function(d) {
          var el = document.getElementById('chain-status');
          if (d.chain_intact) {
            el.innerHTML = '<div class="chain-ok">&#10003; Hash chain intact</div>';
          } else {
            el.innerHTML = '<div class="chain-broken">&#9888; CHAIN INTEGRITY BROKEN at record '
              + d.broken_at_line + ' &mdash; log may have been tampered</div>';
          }
        }).catch(function() {});
    }

    loadEvents();
    checkChain();
  </script>
</body>
</html>
"""


def _build_alerts(traces) -> list:
    """Derive alert list from traces filtered by ALERT_MIN_SEVERITY."""
    min_sev = _SEVERITY_ORDER.get(_ALERT_MIN_SEVERITY, 1)
    alerts = []
    for t in traces:
        sev = _TRACE_SEVERITY.get(t.status.value, "low")
        if _SEVERITY_ORDER.get(sev, 0) >= min_sev:
            reasons = list(t.structural_reasons)
            if t.anomaly_reason:
                reasons.append(t.anomaly_reason)
            alerts.append({
                "icao": t.hex,
                "flight": t.flight.strip() if t.flight else None,
                "status": t.status.value,
                "severity": sev,
                "reasons": reasons,
                "anomaly_score": t.anomaly_score,
            })
    return alerts


def create_app(trace_store=None, forensic_logger=None, heartbeat=None, pipeline_interval=5.0) -> Flask:
    """
    Flask application factory.

    :param trace_store: TraceStore shared with pipeline.
    :param forensic_logger: ForensicLogger instance for audit routes.
    :param heartbeat: 1-item list holding last pipeline cycle timestamp (liveness probe).
    :param pipeline_interval: expected pipeline cycle interval, used to size the liveness window.
    """
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(32))

    if trace_store is None:
        from adsb_secure.trace_store import TraceStore
        trace_store = TraceStore()

    app.trace_store = trace_store
    app.forensic_logger = forensic_logger
    app.heartbeat = heartbeat
    app.pipeline_interval = pipeline_interval

    from web.auth import auth_bp
    app.register_blueprint(auth_bp)

    from web.auth import require_auth, require_role
    from security.forensic_logger import SecurityEvent, EventType, Severity

    # ------------------------------------------------------------------ #
    # Public routes
    # ------------------------------------------------------------------ #

    @app.get("/health")
    def health():
        if app.heartbeat is None:
            return jsonify({"status": "ok", "pipeline": "unknown"})
        age = time.time() - app.heartbeat[0]
        stale = age > max(app.pipeline_interval * 3, 15)
        return jsonify({
            "status": "degraded" if stale else "ok",
            "pipeline": "stale" if stale else "alive",
            "pipeline_age_s": round(age, 1),
        }), (503 if stale else 200)

    # ------------------------------------------------------------------ #
    # Protected routes — all authenticated roles
    # ------------------------------------------------------------------ #

    @app.get("/")
    @require_auth
    def dashboard():
        traces = app.trace_store.all_current()
        suspicious = sum(1 for t in traces if t.status.value == "suspicious")
        alerts = _build_alerts(traces)
        return render_template_string(
            _DASHBOARD_HTML,
            traces=traces,
            suspicious=suspicious,
            alerts=alerts,
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

    @app.get("/analyst/events")
    @require_role("analyst")
    def analyst_events():
        return render_template_string(
            _ANALYST_HTML,
            username=session.get("username", "?"),
        )

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
        app.forensic_logger.log(SecurityEvent(
            event_type=EventType.AUDIT_EXPORT,
            severity=Severity.LOW,
            details={"format": "csv", "exported_by": session.get("username", "?"), "count": len(events)},
        ))
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

    @app.get("/api/export/pdf")
    @require_role("analyst")
    def api_export_pdf():
        if not app.forensic_logger:
            return jsonify({"error": "forensic_logger_not_configured"}), 503
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import cm
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
        except ImportError:
            return jsonify({"error": "reportlab_not_installed"}), 503

        import io
        import datetime
        from flask import Response

        events = app.forensic_logger.read_events(limit=10000)
        chain_ok, broken_at = app.forensic_logger.verify_chain()

        app.forensic_logger.log(SecurityEvent(
            event_type=EventType.AUDIT_EXPORT,
            severity=Severity.LOW,
            details={"format": "pdf", "exported_by": session.get("username", "?"), "count": len(events)},
        ))

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=A4,
            rightMargin=1.5 * cm, leftMargin=1.5 * cm,
            topMargin=2 * cm, bottomMargin=2 * cm,
        )
        styles = getSampleStyleSheet()
        story = []

        now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        story.append(Paragraph("ADS-B Secure — Security Event Report", styles["Title"]))
        story.append(Paragraph(f"Generated: {now_str} | Events: {len(events)}", styles["Normal"]))
        story.append(Spacer(1, 0.3 * cm))

        chain_label = "Chain Integrity: INTACT" if chain_ok else f"Chain Integrity: BROKEN at record {broken_at}"
        story.append(Paragraph(chain_label, styles["Normal"]))
        story.append(Spacer(1, 0.5 * cm))

        if events:
            header = [["Timestamp", "Event Type", "Severity", "ICAO", "Details"]]
            rows = []
            for e in events:
                ts_str = datetime.datetime.utcfromtimestamp(e["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                det = str(e.get("details", {}))
                if len(det) > 55:
                    det = det[:52] + "..."
                rows.append([
                    ts_str,
                    e.get("event_type", ""),
                    (e.get("severity", "")).upper(),
                    e.get("icao") or "—",
                    det,
                ])
            table = Table(header + rows, colWidths=[3.5 * cm, 4 * cm, 2 * cm, 2 * cm, None])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.black),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.green),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                    colors.Color(0.05, 0.05, 0.05),
                    colors.Color(0.09, 0.09, 0.09),
                ]),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            story.append(table)
        else:
            story.append(Paragraph("No events found.", styles["Normal"]))

        doc.build(story)
        buf.seek(0)

        fname = f"adsb_audit_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        return Response(
            buf.getvalue(),
            mimetype="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={fname}"},
        )

    return app
