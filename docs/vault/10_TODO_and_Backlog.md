# TODO and Backlog

## Task immediate (pre-Sprint 1)

- [ ] **Approvare ADR-001** (pygame vs web dashboard) — da decidere con team
- [ ] Creare `requirements.txt` con dipendenze versionate
- [ ] Decidere struttura directory definitiva (`adsb_secure/` vs flat)
- [ ] Verificare che `notebook/samples/testing/sample.json` sia utilizzabile come simulatore

## Sprint 1 Backlog

Vedi [[05_Sprint_Plan#Sprint 1 — Foundation]]

Stato attuale: **Non iniziato**

## Sprint 2 Backlog

Vedi [[05_Sprint_Plan#Sprint 2 — Security Layer]]

Stato attuale: **Bloccato da Sprint 1**

## Sprint 3 Backlog

Vedi [[05_Sprint_Plan#Sprint 3 — Intelligence Layer]]

Stato attuale: **Bloccato da Sprint 2**

## Debito tecnico noto

| Item | File | Priorità | Descrizione |
|---|---|---|---|
| Debug print | `device-rpi/flightdata.py` | Alta | `print("hii ")` e `print(json_data['aircraft'])` in produzione |
| Error handling | `device-rpi/flightdata.py:refresh()` | Alta | Nessun try/except — crash se dump1090 down |
| URL hardcoded | `device-rpi/flightdata.py` | Media | `"http://localhost:8080/data/aircraft.json"` nel codice |
| No requirements.txt | root | Alta | Dipendenze non documentate |
| No tests | tutto | Alta | Zero coverage esistente |
| CNN offline-only | `notebook/Fly_Catcher.ipynb` | Media | Non integrata nella pipeline real-time |

## Blockers

- Nessun blocker critico identificato al 2026-06-03
- ADR-001 (dashboard) è la decisione più urgente prima di Sprint 2

## Ideas / Future

- MLAT cross-validation (richiede infrastruttura — roadmap futura)
- TESLA completo (richiede ricerca aggiuntiva — roadmap futura)
- Integration con OpenSky Network API per cross-validation passiva
- Hardware RPi deployment una volta testato su simulatore
