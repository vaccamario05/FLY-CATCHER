# Project Overview — ADS-B Secure

## Scopo

ADS-B Secure è un **security hardening layer** sopra Fly-catcher.
Non riscrive il sistema: lo estende con validazione, anomaly detection e logging forense.

## Relazione con Fly-catcher

```
[SDR Hardware / dump1090]
        ↓ aircraft.json (HTTP :8080)
[Fly-catcher — Foundation]
  - flightdata.py: fetch + parse JSON
  - AirCraftData: data model
  - piawareradar.py: pygame display (TFT)
  - radar.py: dot rendering
        ↓ (extension points)
[ADS-B Secure — Security Layer]
  - structural validation
  - HMAC verification (PoC)
  - replay detection
  - rate limiting
        ↓
[ADS-B Secure — Intelligence Layer]
  - Isolation Forest anomaly detection
  - trace classification
  - web dashboard
  - forensic logging (hash chaining)
```

## Obiettivi tecnici

1. **Integrità PoC**: HMAC su messaggi simulati/preprocessati
2. **Replay detection**: timestamp window + deduplicazione
3. **Ghost aircraft detection**: Isolation Forest su feature cinematiche
4. **Forensic logging**: append-only con hash chaining SHA-256
5. **Web dashboard**: classificazione tracce (trusted/suspicious/unverified)
6. **Auth minima**: RBAC operatore/analista, password hashate

## Limiti dichiarati del prototipo

- HMAC **non** modifica il protocollo ADS-B reale — solo PoC su dati simulati
- Il sistema opera **solo in ricezione**, mai in trasmissione
- Senza hardware SDR fisico: usa dump1090 + dati simulati da `aircraft.json`
- MLAT non implementato (richiede infrastruttura distribuita)
- PKI e TESLA completo fuori scope

## Target utenti

| Persona | Ruolo | Accesso |
|---|---|---|
| Elena Russo | Controllore di volo | Dashboard — visualizzazione tracce |
| Luca Ferri | Analista sicurezza | Dashboard + log forensi |
| Marco Bianchi | Supervisore operativo | Dashboard + report |
| Marta De Santis | Attaccante SDR | (threat actor, non utente legittimo) |

## Anno accademico

2025/2026 — Università Parthenope Napoli
Corso: Ingegneria e Scienze Informatiche per la Cybersecurity
Docenti: Prof. Luigi Romano, Prof. Luigi Coppolino
Team: Rocco Rizzitano, Mario Vacca
