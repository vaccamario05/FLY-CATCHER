# Commands and Runbook

## Setup ambiente ✅ Sprint 1 completato

```bash
# Navigazione
cd /Users/mariomega05/Documents/Unversita/ProgettoPSS/fly-catcher

# Dipendenze (usa python3.11 — ha pytest e flask installati)
python3.11 -m pip install -r requirements.txt

# Variabili d'ambiente sicurezza (Sprint 2)
export ADSB_HMAC_KEY="$(python3.11 -c 'import secrets; print(secrets.token_hex(32))')"
export DUMP1090_URL="http://localhost:8080/data/aircraft.json"
export RATE_LIMIT_PPS=100
export HMAC_WINDOW_SECONDS=30
```

## Avvio ADS-B Secure ✅ Sprint 1

```bash
# Modalità simulatore (senza hardware SDR)
python3.11 -m adsb_secure --mode simulator --file notebook/samples/testing/sample.json
# → pipeline ogni 5s, dashboard a http://localhost:5000

# Modalità live (con dump1090)
python3.11 -m adsb_secure --mode live --url http://localhost:8080/data/aircraft.json

# Simulatore standalone (CLI)
python3.11 simulator/replay.py --file notebook/samples/testing/sample.json --loop --interval 2

# API routes disponibili Sprint 1:
# GET /health             → {"status":"ok","sprint":1}
# GET /api/traces         → lista tracce con status
# GET /api/aircraft/<hex> → dettaglio + history traccia
# GET /                   → dashboard HTML con auto-refresh 5s
```

## Avvio legacy Fly-catcher (pygame su RPi)

```bash
cd device-rpi
python3 piawareradar.py <lat> <lon> [--piawareip <ip>]

# Esempio locale con simulatore
python3 piawareradar.py 40.85 14.27 --piawareip localhost
```

## Test ✅ 35 passing (Sprint 1)

```bash
# Tutti i test
python3.11 -m pytest tests/ -v

# Solo validator (21 test)
python3.11 -m pytest tests/test_validator.py -v

# Solo simulator (8 test)
python3.11 -m pytest tests/test_simulator.py -v

# Solo web / Flask (5 test)
python3.11 -m pytest tests/test_web.py -v

# Con coverage
python3.11 -m pytest tests/ --cov=adsb_secure --cov=security --cov=simulator --cov-report=term-missing
```

## Security scan ✅ Sprint 1 — 1 Medium residuo (B104, documentato)

```bash
# Static analysis
python3.11 -m bandit -r adsb_secure/ security/ simulator/ web/ -f txt

# Dependency audit
pip install pip-audit
pip-audit

# Risultati da documentare in 11_Bugs_and_Fixes.md
```

## Verifica integrità log

```bash
python3 -c "
from security.forensic_logger import ForensicLogger
logger = ForensicLogger('logs/security_events.jsonl')
result = logger.verify_chain()
print('Chain OK' if result else 'CHAIN BROKEN!')
"
```

## Generazione chiave HMAC

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
# Output esempio: a3f8c2d1e9b4...
# Salvare in .env (non committare mai .env)
```

## Dump1090 (se disponibile hardware SDR)

```bash
# Installazione (Linux/RPi)
sudo apt-get install dump1090-fa

# Avvio con RTL-SDR
dump1090 --interactive --net --quiet

# Verifica feed
curl http://localhost:8080/data/aircraft.json | python3 -m json.tool | head -50
```

## Debug pipeline

```bash
# Verifica che il simulatore produca dati validi
python3 -c "
import json
with open('notebook/samples/testing/sample.json') as f:
    data = json.load(f)
print(f'Aircraft count: {len(data[\"aircraft\"])}')
print(f'First aircraft: {data[\"aircraft\"][0]}')
"
```
