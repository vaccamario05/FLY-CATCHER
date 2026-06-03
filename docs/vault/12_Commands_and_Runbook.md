# Commands and Runbook

## Setup ambiente (da completare in Sprint 1)

```bash
# Clone / navigazione
cd /Users/mariomega05/Documents/Unversita/ProgettoPSS/fly-catcher

# Virtual environment (da creare)
python3 -m venv .venv
source .venv/bin/activate

# Dipendenze (requirements.txt da creare in S1-01)
pip install -r requirements.txt

# Variabili d'ambiente sicurezza (da Sprint 2)
export ADSB_HMAC_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export DUMP1090_URL="http://localhost:8080/data/aircraft.json"
export RATE_LIMIT_PPS=100
export HMAC_WINDOW_SECONDS=30
```

## Avvio simulatore (Sprint 1)

```bash
# Replay JSON esistente (senza hardware SDR)
python3 simulator/replay.py --file notebook/samples/testing/sample.json --loop

# Con velocità artificiale (per test flooding)
python3 simulator/replay.py --file notebook/samples/testing/sample.json --pps 50
```

## Avvio pipeline ADS-B Secure (da Sprint 2)

```bash
# Modalità simulatore
python3 -m adsb_secure --mode simulator --file notebook/samples/testing/sample.json

# Modalità dump1090 (con hardware SDR)
python3 -m adsb_secure --mode live --url http://localhost:8080/data/aircraft.json
```

## Avvio web dashboard (Sprint 2)

```bash
python3 web/app.py
# Dashboard: http://localhost:5000
# API aircraft: http://localhost:5000/api/aircraft
# API audit: http://localhost:5000/api/audit/logs
```

## Avvio legacy Fly-catcher (pygame su RPi)

```bash
cd device-rpi
python3 piawareradar.py <lat> <lon> [--piawareip <ip>]

# Esempio locale con simulatore
python3 piawareradar.py 40.85 14.27 --piawareip localhost
```

## Test

```bash
# Tutti i test
python3 -m pytest tests/ -v

# Solo validator
python3 -m pytest tests/test_validator.py -v

# Solo security layer
python3 -m pytest tests/test_hmac.py tests/test_replay.py tests/test_rate.py -v

# Con coverage
python3 -m pytest tests/ --cov=adsb_secure --cov-report=term-missing
```

## Security scan

```bash
# Static analysis
pip install bandit
bandit -r device-rpi/ security/ web/ ml/ -f txt

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
