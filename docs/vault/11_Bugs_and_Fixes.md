# Bugs and Fixes

## [SECURITY-001] Input non validato in flightdata.py

**Trovato**: 2026-06-03
**File**: `device-rpi/flightdata.py`
**Severità**: Alta
**Stato**: Aperto — fix pianificato in Sprint 1 (S1-03)

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
**Stato**: Aperto — fix in Sprint 1 (S1-06)

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
**Stato**: Aperto — fix in Sprint 1 (S1-07)

**Descrizione**:
Se dump1090 non è raggiungibile, `urlopen()` lancia `urllib.error.URLError`.
Non c'è try/except → crash dell'applicazione.

**Fix**: Aggiungere try/except con fallback a ultimo dataset valido + log evento.

---

## [BUG-003] URL hardcoded in flightdata.py

**Trovato**: 2026-06-03
**File**: `device-rpi/flightdata.py:4`
**Severità**: Media
**Stato**: Aperto — fix in Sprint 1

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

