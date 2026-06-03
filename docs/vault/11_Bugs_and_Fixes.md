# Bugs and Fixes

## [PIP-AUDIT-001] CVE urllib3 — dipendenza transitiva Flask

**Trovato**: 2026-06-03 (pip-audit sessione finale)
**Package**: urllib3 2.2.3 (installato transitivamente da Flask/werkzeug)
**CVE**: CVE-2025-50182, CVE-2025-50181, CVE-2025-66418, CVE-2025-66471, CVE-2026-21441
**Fix disponibile**: urllib3 ≥ 2.5.0 / 2.6.0 / 2.6.3
**Stato**: Non urgente — impatto limitato a PoC locale senza TLS esterno

**Nota**: torch CVE (PYSEC-2025-*) — torch NON è dipendenza del progetto, è installato globalmente nell'ambiente Python di sistema. Non nel `requirements.txt`.

**Azione**: quando si fa `pip install -r requirements.txt` in un ambiente pulito le versioni aggiornate di flask traineranno urllib3 aggiornata. Documentato per audit.

---

## [BANDIT-002] B301/B403 pickle — risolto con joblib

**Trovato**: 2026-06-03 (bandit Sprint 3)
**File**: `ml/anomaly_detector.py`
**Severità originale**: 2× Medium (B301, B403)
**Stato**: ✅ Risolto — sostituito `pickle` con `joblib` (sklearn-recommended)

**Fix**: `import joblib` + `joblib.dump()` / `joblib.load()` invece di `pickle.dump/load`.

---

## [BANDIT-003] B112 try/except/continue — accettato in training script

**Trovato**: 2026-06-03 (bandit sessione finale)
**File**: `ml/train.py:59`
**Severità**: Low (B112)
**Stato**: Documentato — accettato

**Motivazione**: il training script salta record malformati nei samples — comportamento corretto. Non è un problema di sicurezza.

---

## [BANDIT-001] B104 — Binding su tutte le interfacce (residuo accettato)

**Trovato**: 2026-06-03 (bandit Sprint 1)
**File**: `adsb_secure/__main__.py:88`
**Severità**: Medium (Bandit B104)
**Stato**: Documentato — accettato per PoC locale

**Descrizione**: `flask_app.run(host="0.0.0.0")` lega il server a tutte le interfacce.
**Motivazione accettazione**: il progetto è un prototipo locale/accademico. In produzione → `host="127.0.0.1"` o reverse proxy.

---

## [SECURITY-001] Input non validato in flightdata.py

**Trovato**: 2026-06-03
**File**: `device-rpi/flightdata.py`
**Severità**: Alta
**Stato**: ✅ Risolto in Sprint 1 — `security/validator.py` creato

**Descrizione**:
`AirCraftData.parse_flightdata_json()` accetta tutti i campi del JSON senza validazione.
Un pacchetto malevolo con valori fuori range (lat=9999, altitude=-99999, hex="../../etc")
viene accettato e renderizzato senza alcun controllo.

**Root cause**: Nessun validation layer nel path di ingestione dati.

**Fix pianificato**: `security/validator.py` con check strutturali pre-parse.

---

## [BUG-001] Debug print in produzione

**Trovato**: 2026-06-03
**File**: `device-rpi/flightdata.py:25,30`
**Severità**: Bassa
**Stato**: ✅ Risolto in Sprint 1 — rimossi tutti i debug print

**Descrizione**:
```python
print("hii ")
print(json_data['aircraft'])
```
Stampa l'intero array aircraft.json sul terminale ad ogni refresh.
Potenziale leakage di dati + degrado performance.

**Fix**: Rimuovere print o sostituire con `logging.debug()`.

---

## [BUG-002] Nessun error handling in refresh()

**Trovato**: 2026-06-03
**File**: `device-rpi/flightdata.py:refresh()`
**Severità**: Alta
**Stato**: ✅ Risolto in Sprint 1 — try/except URLError + fallback a _last_json

**Descrizione**:
Se dump1090 non è raggiungibile, `urlopen()` lancia `urllib.error.URLError`.
Non c'è try/except → crash dell'applicazione.

**Fix**: Aggiungere try/except con fallback a ultimo dataset valido + log evento.

---

## [BUG-003] URL hardcoded in flightdata.py

**Trovato**: 2026-06-03
**File**: `device-rpi/flightdata.py:4`
**Severità**: Media
**Stato**: ✅ Risolto in Sprint 1 — `refresh()` usa `self.data_url`

**Descrizione**:
```python
DUMP1090DATAURL = "http://localhost:8080/data/aircraft.json"
```
E poi di nuovo hardcoded dentro `refresh()`:
```python
self.req = urlopen("http://localhost:8080/data/aircraft.json")
```
Due definizioni separate — `data_url` parametro del costruttore non viene usato in `refresh()`.

**Fix**: Usare `self.data_url` in `refresh()` e leggere URL da config/env.

---

## [SECURITY-002] Nessun sanitization stringhe per display

**Trovato**: 2026-06-03
**File**: `device-rpi/piawareradar.py`
**Severità**: Media
**Stato**: Aperto

**Descrizione**:
I campi `hex`, `squawk`, `flight` vengono resi direttamente come testo pygame.
Su web dashboard, se non sanitizzati → potenziale XSS.

**Fix Sprint 2**: Sanitizzazione in `Normalizer` prima di passare a dashboard web.

