# Security Model

## Minacce (STRIDE su ADS-B Secure)

| Categoria | Minaccia | Asset | Gravità | Mitigazione | Stato |
|---|---|---|---|---|---|
| Spoofing | Ghost aircraft injection | Pacchetti ADS-B, dashboard | Alta | Anomaly detection IF, classificazione conservativa | Sprint 3 |
| Spoofing | ICAO address falsificato | ICAO, traccia | Alta | Structural validation, IF | Sprint 1+3 |
| Tampering | Altitude/velocity tampering | Posizione, quota | Critica | HMAC PoC, range validation | Sprint 2 |
| Tampering | Log manipulation | Log forensi | Alta | Hash chaining append-only | Sprint 2 |
| Repudiation | Log repudiation | Audit trail | Alta | SHA-256 chain — rottura rilevabile | Sprint 2 |
| Info Disclosure | Unauthorized tracking | Dashboard, log, report | Media | Auth + RBAC, timeout sessione | Sprint 2 |
| Denial of Service | Packet flooding | Pipeline, dashboard | Alta | Rate limiting, queue management | Sprint 2 |
| Elevation of Privilege | Dashboard unauthorized access | Dashboard, log | Alta | RBAC, hashed passwords, session timeout | Sprint 2 |

## Misuse Case — Stato mitigazioni

| MC | Nome | Mitigazione implementata | Sprint |
|---|---|---|---|
| MC1 | Ghost Aircraft Injection | Anomaly detection IF | 3 |
| MC2 | Replay Attack | Timestamp validation + dedup | 2 |
| MC3 | Altitude/Velocity Tampering | HMAC PoC + structural check | 2 |
| MC4 | SDR Packet Flood | Rate limiting | 2 |
| MC5 | Unauthorized Tracking | RBAC + auth | 2 |
| MC6 | Log Repudiation | Hash chaining | 2 |
| MC7 | False Alert Triggering | Alert aggregation + soglie | 3 |
| MC8 | Dashboard unauthorized access | Auth + RBAC | 2 |

## Controlli implementati

### Strutturali (Sprint 1)
- Validazione CRC formato pacchetto ADS-B
- Verifica ICAO address (formato hex 6 char)
- Verifica range lat/lon (-90/90, -180/180)
- Verifica range altitude (realistico per aviazione civile)
- Sanitizzazione stringhe (hex, flight callsign) prima del rendering

### Crittografici (Sprint 2 — PoC)
- HMAC-SHA256 su campi critici: ICAO, lat, lon, altitude, timestamp
- Chiave da variabile d'ambiente `ADSB_HMAC_KEY` (mai hardcoded)
- Funziona solo su dati preprocessati con chiave condivisa
- **Limitazione dichiarata**: NON è autenticazione reale del protocollo ADS-B

### Temporali (Sprint 2)
- Finestra temporale configurabile (default: 30s)
- Deduplicazione su (ICAO, timestamp, posizione)
- Messaggio fuori finestra → SUSPICIOUS + log event

### Disponibilità (Sprint 2)
- Token bucket: max N pacchetti/sec configurabile
- Overflow → log event + scarto

### Logging forense (Sprint 2)
- File append-only: `logs/security_events.jsonl`
- Ogni record: `{id, timestamp, event_type, severity, icao, details, prev_hash, hash}`
- `prev_hash` = SHA-256(record precedente)
- Rottura chain → alert immediato

### Autenticazione (Sprint 2)
- Login con username/password
- Password hashata con `werkzeug.security.generate_password_hash` (PBKDF2-SHA256)
- Ruoli: `operator` (solo view), `analyst` (view + log + export)
- Session timeout: 30 minuti inattività
- Falliti login: loggati in audit log

## Controlli mancanti (rischio residuo)

| Controllo | Perché mancante | Rischio residuo |
|---|---|---|
| Autenticità pacchetti radio ADS-B | Limite strutturale del protocollo | Alto — strutturale |
| TESLA / autenticazione broadcast | Richiede infrastruttura globale | Alto — fuori scope |
| MLAT cross-validation | Richiede rete fisica distribuita | Medio — fuori scope |
| TLS per API interna | Non richiesto per PoC locale | Basso — PoC locale |
| HSM per HMAC key storage | Fuori scope universitario | Basso — PoC locale |

## Principi di sicurezza applicati

- **Secure by Design**: security layer nella pipeline, non aggiunto dopo
- **Least Privilege**: ruoli separati operatore/analista
- **Fail-Safe**: default → UNVERIFIED, mai VALID per ambiguità
- **Defense in Depth**: validator → HMAC → replay → rate → ML → logger
- **Complete Mediation**: ogni pacchetto attraversa tutti i layer
- **Economy of Mechanism**: HMAC-SHA256 pre-shared key (semplice e sufficiente per PoC)
