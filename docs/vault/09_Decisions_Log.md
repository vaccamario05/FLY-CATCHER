# Decisions Log (ADR)

## ADR-001 — Dashboard: pygame vs Web

**Data**: 2026-06-03
**Stato**: DECISO ✅ (approvato 2026-06-03)

**Contesto**:
Fly-catcher usa pygame su TFT screen 3.5" per Raspberry Pi.
ADS-B Secure richiede dashboard accessibile con stati di sicurezza, alert, log forensi, RBAC.

**Opzioni valutate**:

| Opzione | Pro | Contro |
|---|---|---|
| A: Flask + HTML/JS (browser) | Multi-utente, RBAC, sessioni, log viewer, export | Richiede nuovo frontend |
| B: Estendere pygame | Mantiene Fly-catcher inalterato | Non multi-utente, impossibile RBAC |
| C: Dual mode | Compatibilità totale | Doppio maintenance burden |

**Decisione**: Opzione A — Flask come UI strategica principale

**Motivazione**:
- RBAC + sessioni richiedono HTTP — impossibile con pygame single-user
- Log viewer, export CSV, alert panel → naturale via browser
- Pipeline dati separata dalla presentazione → riusabilità moduli
- pygame rimane disponibile come display legacy/demo su RPi fisico

**Impatto**:
- Nuovo modulo `web/` con Flask (Sprint 2)
- Pipeline dati (`security/`, `ml/`) completamente disaccoppiata dalla UI
- `device-rpi/piawareradar.py` diventa componente opzionale, non più entrypoint strategico
- Nuovo entrypoint: `web/app.py` o `adsb_secure/__main__.py`

---

## ADR-002 — ML: CNN Keras vs Isolation Forest

**Data**: 2026-06-03
**Stato**: DECISO

**Contesto**:
Fly-catcher ha già `Spoof_Detection.h5` (CNN Keras, addestrata su dati etichettati).
ADS-B Secure specifica Isolation Forest (non supervisionato).

**Decisione**: Isolation Forest come componente principale, CNN come modulo opzionale

**Motivazione**:
- Dataset etichettato limitato → IF funziona senza labels
- IF più interpretabile (anomaly_score continuo, motivazione)
- CNN richiederebbe TensorFlow (pesante) in produzione; IF usa scikit-learn già presente
- CNN può essere usata in parallelo come "secondo parere" in Sprint 3 se tempo permette

**Rischio**: IF può avere FP più alti su dati di training limitati → calibrazione soglie necessaria

---

## ADR-003 — HMAC: chiave pre-condivisa via env

**Data**: 2026-06-03
**Stato**: DECISO

**Contesto**:
HMAC richiede chiave condivisa. Come gestirla in un PoC?

**Decisione**: Variabile d'ambiente `ADSB_HMAC_KEY`, generata casualmente al setup, documentata nel runbook.

**Motivazione**:
- Niente hardcoding (regola non negoziabile)
- Env var è il pattern standard per secrets in sviluppo
- Simulatore preprocessa i pacchetti con la stessa chiave → PoC coerente

---

## ADR-004 — Struttura directory: estensione vs fork

**Data**: 2026-06-03
**Stato**: DECISO

**Contesto**:
Aggiungere codice al repo Fly-catcher esistente o creare struttura parallela?

**Decisione**: Estensione modulare nella stessa repo, nuove directory `security/`, `web/`, `ml/`, `tests/`, `docs/`

**Motivazione**:
- Un solo repo = un solo contesto per il team universitario
- Fly-catcher `device-rpi/` rimane intatto (retrocompatibilità)
- Nuovi moduli non dipendono da pygame → testabili standalone

---

## ADR-005 — Simulatore: replay JSON vs generatore sintetico

**Data**: 2026-06-03
**Stato**: DECISO

**Contesto**:
Senza dump1090 su macOS, come sviluppare e testare la pipeline?

**Decisione**: Replay JSON da `notebook/samples/` come modalità primaria di sviluppo.

**Motivazione**:
- Samples già presenti nel repo
- Reproducibilità: stesso file → stesso comportamento
- `Spoofed_Aircraft_Generator.ipynb` già disponibile per generare dati sintetici malevoli
- Nessuna dipendenza hardware per sviluppo

