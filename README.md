# ADS-B Secure

> **Protecting Air Traffic. Securing the Skies.**

ADS-B Secure è un security hardening layer per sistemi di monitoraggio del traffico aereo basati su ADS-B. Costruito come estensione modulare sopra [Fly-catcher](https://github.com/ANG13T/fly-catcher), aggiunge validazione crittografica, anomaly detection e logging forense a un protocollo strutturalmente non autenticato.

---

## Contesto accademico

| Campo | Valore |
|---|---|
| Università | Università degli Studi di Napoli Parthenope |
| Dipartimento | Dipartimento di Ingegneria |
| Corso | Ingegneria e Scienze Informatiche per la Cybersecurity |
| Materia | Progettazione di Software Sicuro |
| Docenti | Prof. Luigi Romano, Prof. Luigi Coppolino |
| Anno accademico | 2025/2026 |
| Autori | Rocco Rizzitano, Mario Vacca |

---

## Cos'è ADS-B e perché è vulnerabile

ADS-B (Automatic Dependent Surveillance-Broadcast) è il protocollo aeronautico che trasmette posizione, velocità e identità degli aeromobili in broadcast radio a 1090 MHz. È usato globalmente per il monitoraggio del traffico aereo.

**Problema**: ADS-B è stato progettato senza meccanismi di autenticazione, integrità o cifratura. Chiunque con un ricevitore SDR può:
- Iniettare aerei fantasma (ghost aircraft injection)
- Modificare quota e velocità di aerei reali (altitude/velocity tampering)
- Ritrasmettere pacchetti catturati in precedenza (replay attack)
- Saturare la pipeline di ricezione (packet flooding / DoS)

**Soluzione**: ADS-B Secure introduce un layer software di controllo a valle della ricezione che rileva e mitiga queste minacce senza modificare il protocollo aeronautico reale.

---

## Architettura

```
[dump1090 / Simulatore JSON]
        ↓ raw ADS-B packets (untrusted)
[RateLimiter]          → blocca flooding (token bucket)
[StructuralValidator]  → verifica formato, range fisici
[HMACValidator]        → integrità payload (PoC, chiave pre-condivisa)
[ReplayDetector]       → timestamp window + deduplicazione
[Classifier]           → TraceStatus: VALID / SUSPICIOUS / UNVERIFIED / INVALID
[AnomalyDetector]      → Isolation Forest su feature cinematiche
[ForensicLogger]       → JSONL append-only, SHA-256 hash chaining
        ↓
[Flask Dashboard]      → mappa Leaflet.js + RBAC operator/analyst
```

---

## Funzionalità

### Foundation Layer
- Acquisizione da dump1090 HTTP API o simulatore JSON (senza hardware SDR)
- Normalizzazione campi ADS-B con gestione varianti dump1090 e ADSB Exchange
- Simulatore offline con replay di campioni reali

### Security Layer
- **Validazione strutturale**: ICAO format, lat/lon range, altitude, speed, track, flight callsign
- **HMAC-SHA256 (PoC)**: verifica integrità payload su dati simulati/preprocessati con chiave da env
- **Replay detection**: finestra temporale configurabile + bounded dedup set
- **Rate limiting**: token bucket configurabile via env (`RATE_LIMIT_PPS`)
- **Logging forense**: JSONL append-only con SHA-256 hash chaining tamper-evident
- **Auth e RBAC**: ruoli operator/analyst, password PBKDF2-SHA256, session timeout 30 min

### Intelligence Layer
- **Feature extraction**: delta posizione/velocità/quota, haversine distance, speed discrepancy
- **Isolation Forest**: anomaly detection non supervisionato (scikit-learn), score continuo
- **Training su dati reali**: ~8.500 record da campioni ADSB Exchange + augmentazione sintetica
- **Dashboard Leaflet.js**: marker colorati per status (verde/arancione/rosso), popup con dettagli

---

## Limiti dichiarati del prototipo

- HMAC opera **solo su dati simulati/preprocessati** — non modifica il protocollo ADS-B reale
- Il sistema opera **solo in ricezione**, mai in trasmissione (vincolo RE-01)
- MLAT, TESLA completo e PKI distribuita sono fuori scope
- Il prototipo non è certificato per uso operativo aeronautico

---

## Avvio rapido

**Requisiti**: Python 3.11+

```bash
# 1. Installa dipendenze
python3.11 -m pip install -r requirements.txt

# 2. Addestra Isolation Forest (solo la prima volta)
python3.11 -m ml.train --samples notebook/samples --augment 200

# 3. Avvia pipeline + dashboard
export ADSB_HMAC_KEY=$(python3.11 -c 'import secrets; print(secrets.token_hex(32))')
python3.11 -m adsb_secure --mode simulator
```

Apri `http://localhost:5000` e accedi con:

| Utente | Password | Accesso |
|---|---|---|
| `operator` | `operator123` | Dashboard + tracce |
| `analyst` | `analyst123` | Dashboard + log forensi + export CSV |

### Demo attacchi

```bash
# In un secondo terminale (chiave generata automaticamente)
python3.11 -m demo.inject_attack --attack all
```

Scenari disponibili: `ghost` · `ghost_valid` · `replay` · `tamper` · `flood`

---

## Test e qualità

```bash
# Suite completa (97 test)
python3.11 -m pytest tests/ -v

# Static analysis
python3.11 -m bandit -r adsb_secure/ security/ ml/ web/ -f txt
# → 0 High, 0 Medium, 1 Low (B112 accettato)
```

---

## Struttura repository

```
adsb_secure/       pipeline principale (acquisition, normalizer, trace_store)
security/          validator, hmac_validator, replay_detector, rate_limiter,
                   forensic_logger, classifier
ml/                feature_extractor, anomaly_detector, train
web/               Flask app (dashboard, auth RBAC)
simulator/         JSONSimulator, HMACPreprocessor
demo/              inject_attack.py, start_demo.sh, demo_script.md
tests/             97 test (10 moduli)
docs/vault/        Vault Obsidian — memoria persistente del progetto
docs/appendice_tecnica.md  appendice tecnica per documentazione accademica
device-rpi/        Fly-catcher originale (display legacy su Raspberry Pi)
notebook/          notebook ML originali Fly-catcher (solo riferimento)
```

---

## Progetto basato su Fly-catcher

Questo progetto accademico usa [Fly-catcher](https://github.com/ANG13T/fly-catcher) di
**Angelina Tsuboi** come punto di partenza per la ricezione e visualizzazione di base
dei dati ADS-B. Fly-catcher è distribuito con licenza MIT (Copyright © 2023 Angelina Tsuboi).

Il codice originale di Fly-catcher è preservato nelle directory `device-rpi/` e `notebook/`
senza modifiche sostanziali (salvo piccoli bug fix documentati).

Tutte le estensioni di sicurezza e intelligenza sviluppate per questo progetto
(`adsb_secure/`, `security/`, `ml/`, `web/`, `simulator/`, `tests/`, `demo/`)
sono lavoro originale degli autori e sono distribuite con licenza MIT separata.

---

## Licenza

Vedi [LICENSE](LICENSE) per il testo completo.

- Codice Fly-catcher originale: **MIT** — Copyright © 2023 Angelina Tsuboi
- Estensioni ADS-B Secure: **MIT** — Copyright © 2025-2026 Rocco Rizzitano, Mario Vacca — Università Parthenope Napoli
