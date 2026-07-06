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
- Tracciare passivamente rotte e movimenti (unauthorized tracking)

**Soluzione**: ADS-B Secure introduce un layer software di controllo a valle della ricezione che rileva e mitiga queste minacce senza modificare il protocollo aeronautico reale.

---

## Architettura

```
[dump1090 / Simulatore JSON]
        ↓ raw ADS-B packets (untrusted)
[RateLimiter]          → blocca flooding (token bucket, soglia configurabile a runtime)
[StructuralValidator]  → verifica formato, range fisici → INVALID se non conforme
[HMACValidator]        → integrità payload (PoC, chiave pre-condivisa)
[ReplayDetector]       → timestamp window + deduplicazione
[AnomalyDetector]      → Isolation Forest su feature cinematiche (ghost aircraft, live in pipeline)
[Classifier]           → TraceStatus: VALID / SUSPICIOUS / UNVERIFIED / INVALID (fail-safe: mai VALID per default)
[ForensicLogger]       → JSONL append-only, SHA-256 hash chaining
        ↓
[Flask Dashboard]      → mappa Leaflet.js, alert panel, RBAC operator/supervisor/analyst
```

Ogni pacchetto attraversa la catena completa prima di essere mostrato o archiviato: in caso di dubbio o eccezione, il sistema declassa la traccia (`SUSPICIOUS`/`UNVERIFIED`), non la promuove mai a `VALID` per inerzia (fail-safe defaults, no failing-open).

---

## Funzionalità

### Foundation Layer
- Acquisizione da dump1090 HTTP API o simulatore JSON (senza hardware SDR)
- Normalizzazione campi ADS-B con gestione varianti dump1090 e ADSB Exchange
- Simulatore offline con replay di campioni reali
- Modalità esclusivamente passiva: nessuna funzionalità di trasmissione

### Security Layer
- **Validazione strutturale**: ICAO format, lat/lon range, altitude, speed, track, squawk, flight callsign
- **HMAC-SHA256 (PoC)**: verifica integrità payload su dati simulati/preprocessati con chiave da env — non autentica il protocollo ADS-B reale
- **Replay detection**: finestra temporale configurabile + bounded dedup set
- **Rate limiting**: token bucket, soglia configurabile a runtime dall'analista
- **Logging forense**: JSONL append-only con SHA-256 hash chaining tamper-evident, verifica integrità catena via API
- **Auth e RBAC**: ruoli `operator` / `supervisor` / `analyst`, password PBKDF2-SHA256, session timeout 30 min, nessuna credenziale hardcoded (password generata e loggata se non configurata via env)
- **Configurazione soglie runtime**: rate limit, finestra replay, soglia anomaly, severità alert — modificabili solo da `analyst`, ogni modifica tracciata nel log forense
- **Error handling fail-safe**: eccezioni non gestite non espongono mai stack trace al client, solo messaggio generico + log server-side

### Intelligence Layer
- **Feature extraction**: delta posizione/velocità/quota, haversine distance, speed discrepancy
- **Isolation Forest**: anomaly detection non supervisionato (scikit-learn), score continuo, wired end-to-end nella pipeline live
- **Training su dati reali**: ~8.500 record da campioni ADSB Exchange + augmentazione sintetica
- **Dashboard Leaflet.js**: marker colorati per status, alert panel con timestamp e motivazione, pagina eventi per analisti con filtri
- **Export audit**: report CSV/PDF degli eventi di sicurezza, solo per `analyst`

---

## Limiti dichiarati del prototipo

- HMAC opera **solo su dati simulati/preprocessati** — non modifica il protocollo ADS-B reale
- Il sistema opera **solo in ricezione**, mai in trasmissione (vincolo RE-01)
- La verifica CRC del frame Mode S grezzo è demandata al decoder upstream (dump1090/PiAware), non reimplementata
- La natura broadcast del protocollo rende l'unauthorized tracking strutturalmente non eliminabile via software
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

# 3. Configura credenziali dashboard (obbligatorio — nessun default hardcoded)
export OPERATOR_PASSWORD=$(python3.11 -c 'import secrets; print(secrets.token_urlsafe(16))')
export ANALYST_PASSWORD=$(python3.11 -c 'import secrets; print(secrets.token_urlsafe(16))')
echo "Operator: $OPERATOR_PASSWORD"
echo "Analyst:  $ANALYST_PASSWORD"

# 4. Avvia pipeline + dashboard
export ADSB_HMAC_KEY=$(python3.11 -c 'import secrets; print(secrets.token_hex(32))')
python3.11 -m adsb_secure --mode simulator
```

Apri `http://localhost:5000` e accedi con le credenziali stampate al passo 3.
Se una password non viene configurata, il sistema ne genera una casuale all'avvio e la scrive nei log del server (mai un valore statico noto).

| Ruolo | Accesso |
|---|---|
| `operator` | Dashboard + tracce |
| `supervisor` | Dashboard + tracce (privilegio intermedio) |
| `analyst` | Dashboard + log forensi + export CSV/PDF + configurazione soglie |

### Test su traffico reale (ADS-B Exchange)

Invece del simulatore, la pipeline può leggere da un feed HTTP esterno pubblico. ADS-B Exchange (readsb-based) usa lo stesso schema JSON per-record di dump1090 (`hex`, `alt_baro`, `gs`, ...), quindi è già compatibile — serve solo l'URL e, se richiesta, una API key:

```bash
export DUMP1090_URL="https://adsbexchange-com1.p.rapidapi.com/v2/lat/<lat>/lon/<lon>/dist/<km>/"
export ADSB_HTTP_HEADERS='{"X-RapidAPI-Key": "<la-tua-chiave>", "X-RapidAPI-Host": "adsbexchange-com1.p.rapidapi.com"}'
python3.11 -m adsb_secure --mode live
```

Nota: dati reali esterni non avranno mai un tag HMAC valido (nessun feed pubblico firma con la tua chiave PoC) → ogni traccia sarà classificata `UNVERIFIED`, mai `VALID`. Comportamento atteso, utile per testare validator/replay/anomaly detection su traffico genuino — il path HMAC resta verificabile solo in modalità simulator.

### Demo attacchi

```bash
# Script guidato (genera chiave HMAC e credenziali automaticamente)
./demo/start_demo.sh

# In un secondo terminale
python3.11 -m demo.inject_attack --attack all
```

Scenari disponibili: `ghost` · `ghost_valid` · `replay` · `tamper` · `flood`

---

## Test e qualità

```bash
# Suite completa (119 test)
python3.11 -m pytest tests/ -v

# Static analysis
python3.11 -m bandit -r adsb_secure/ security/ ml/ web/ -f txt
```

La suite include test funzionali, di sicurezza (HMAC, replay, RBAC, forensic chain) e di performance (latenza pipeline, packet loss sotto rate limiting) — vedi `tests/test_perf.py`.

---

## Struttura repository

```
adsb_secure/       pipeline principale (acquisition, normalizer, trace_store)
security/          validator, hmac_validator, replay_detector, rate_limiter,
                   forensic_logger, classifier
ml/                feature_extractor, anomaly_detector, train
web/               Flask app (dashboard, auth RBAC, config soglie, export audit)
simulator/         JSONSimulator, HMACPreprocessor
demo/              inject_attack.py, start_demo.sh, demo_script.md
tests/             119 test (12 moduli, incl. perf, acquisition multi-provider)
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
