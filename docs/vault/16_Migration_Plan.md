# Migration Plan — Fly-catcher → ADS-B Secure Flask backend

Creato: 2026-06-03 | ADR-001 approvato

## Principio

**Non riscrivere Fly-catcher. Costruire ADS-B Secure accanto a esso.**

Fly-catcher in `device-rpi/` rimane intatto (salvo bug fix minori in Sprint 1).
ADS-B Secure cresce in directory parallele: `adsb_secure/`, `security/`, `web/`, `ml/`.

## Mappa di riuso

| Componente Fly-catcher | Riuso in ADS-B Secure | Come |
|---|---|---|
| `flightdata.py:DUMP1090DATAURL` | `adsb_secure/acquisition.py` | Costante URL reimportata o replicata |
| `flightdata.py:AirCraftData` | `adsb_secure/normalizer.py` | Estesa con campi sicurezza + status |
| `flightdata.py:parse_flightdata_json()` | `adsb_secure/normalizer.py` | Logica parse riutilizzata, sanitizzata |
| `flightdata.py:_refresh()` | `simulator/replay.py` | Modalità offline estesa |
| `gpsutils.py:lat_lon_to_x_y()` | `web/templates/dashboard.html` | Opzionale per mappa JS |
| `notebook/samples/*.json` | `simulator/replay.py` | Dataset di sviluppo |
| `notebook/Spoof_Detection.h5` | `ml/anomaly_detector.py` | Opzionale come "secondo parere" ML |

## Step-by-step migrazione

### STEP 0 — Pre-Sprint 1: struttura base (< 1 ora)

```bash
mkdir -p adsb_secure security ml web/routes web/templates simulator tests
touch adsb_secure/__init__.py adsb_secure/__main__.py
touch security/__init__.py ml/__init__.py web/__init__.py simulator/__init__.py
```

### STEP 1 — Sprint 1: fix Fly-catcher + nuovi moduli fondazione

**1a. Patch `device-rpi/flightdata.py`** (non rimuovere, solo fixare):
- Rimuovere `print("hii ")` e `print(json_data['aircraft'])`
- Aggiungere try/except in `refresh()` con fallback a ultimo dataset
- Correggere: usare `self.data_url` invece di URL hardcoded in `refresh()`

**1b. Creare `adsb_secure/normalizer.py`**:
- Copiare logica `parse_flightdata_json()` come base
- Aggiungere campo `status: TraceStatus = TraceStatus.UNVERIFIED`
- Aggiungere: `anomaly_score`, `anomaly_reason`, `received_at`, `hmac_valid`, `replay_detected`, `structural_valid`
- Costruttore da dict (da JSON) invece che da argomenti posizionali

**1c. Creare `adsb_secure/acquisition.py`**:
- `DataIngestion.fetch()` → chiama HTTP dump1090 o simulator
- Ritorna lista raw dicts (JSON parsed, non ancora AirCraftData)

**1d. Creare `simulator/replay.py`**:
- Legge `notebook/samples/testing/sample.json`
- Restituisce lista raw dicts
- Opzionale: `--loop` e `--pps N` per controllo velocità

**1e. Creare `security/validator.py`**:
- `StructuralValidator.validate(raw_dict) → ValidationResult`
- Check: ICAO hex format, lat/lon range, altitude range, speed range
- Ritorna `(is_valid: bool, reasons: list[str])`

### STEP 2 — Sprint 2: security layer + Flask

**2a. Creare moduli security**:
- `security/hmac_validator.py` → HMAC-SHA256, key da env
- `security/replay_detector.py` → window + bounded dedup
- `security/rate_limiter.py` → token bucket
- `security/forensic_logger.py` → append JSONL + chain

**2b. Creare `web/app.py`** (Flask factory):

```python
from flask import Flask
from web.auth import auth_bp
from web.routes.aircraft import aircraft_bp

def create_app(pipeline):
    app = Flask(__name__)
    app.secret_key = os.environ['FLASK_SECRET_KEY']
    app.register_blueprint(auth_bp)
    app.register_blueprint(aircraft_bp)
    return app
```

**2c. Pipeline wiring** in `adsb_secure/pipeline.py`:
```
fetch → rate_limit → validate → hmac_check → replay_check → classify → store → log
```

**2d. Flask consuma pipeline** via `TraceStore` condiviso:
- `GET /api/aircraft` → legge `TraceStore` in-memory → JSON response
- Dashboard HTML + JS polling ogni 5s su `/api/aircraft`

**2e. Auth** → `web/auth.py`:
- Login form → `werkzeug.check_password_hash`
- Session con `flask.session`, timeout 30min
- `@require_role('analyst')` decorator per rotte protette

### STEP 3 — Sprint 3: ML layer

**3a. Creare `ml/feature_extractor.py`**:
- Input: `deque[AirCraftData]` per un ICAO
- Output: `dict[str, float]` con delta_lat, delta_lon, delta_alt, delta_speed, heading_change, time_delta

**3b. Creare `ml/anomaly_detector.py`**:
- Training su samples legittimi da `notebook/samples/`
- `predict(feature_vector) → (score: float, reason: str)`
- Score > threshold → SUSPICIOUS

**3c. Integrare ML in pipeline** post-classify:
- `TraceScorer.score(classified_aircraft, feature_vector) → AirCraftData` (con anomaly_score)

**3d. Dashboard avanzata**:
- Colori: verde=VALID, arancio=UNVERIFIED, rosso=SUSPICIOUS
- Dettaglio per traccia: anomaly_score, reason, timestamp
- Alert panel: eventi SUSPICIOUS aggregati

## Dipendenze nuove (requirements.txt)

```
flask>=3.0
werkzeug>=3.0
scikit-learn>=1.4
numpy>=1.26
pytest>=8.0
pytest-cov>=5.0
bandit>=1.7
pip-audit>=2.7
```

TensorFlow/Keras → opzionale, non nel requirements.txt principale.

## Cosa NON fare durante la migrazione

- Non eliminare `device-rpi/piawareradar.py` — rimane come display legacy RPi
- Non modificare `notebook/` — i notebook sono read-only reference
- Non toccare `notebook/Spoof_Detection.h5` — preservare per uso opzionale
- Non aggiungere TensorFlow nel requirements principale — troppo pesante per pipeline
- Non accoppiare `security/` a Flask — i moduli sicurezza devono essere testabili standalone

## Verifica migrazione completata (checklist finale)

```bash
# Pipeline standalone senza Flask
python3 -c "
from simulator.replay import JSONSimulator
from security.validator import StructuralValidator
from adsb_secure.normalizer import build_aircraft_data

sim = JSONSimulator('notebook/samples/testing/sample.json')
validator = StructuralValidator()
for raw in sim.fetch():
    result = validator.validate(raw)
    print(result.status)
"

# Flask dashboard avviata
python3 -m adsb_secure
# → http://localhost:5000 risponde

# Test suite verde
python3 -m pytest tests/ -v

# Fly-catcher legacy ancora funzionante (opzionale)
cd device-rpi && python3 -c "from flightdata import FlightData; print('OK')"
```
