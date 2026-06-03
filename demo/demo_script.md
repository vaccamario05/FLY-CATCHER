# Script Demo — ADS-B Secure
## Registrazione video per esame (3-5 minuti)
### Progettazione di Software Sicuro — Prof. Romano, Prof. Coppolino

---

## Pre-registrazione: setup ambiente (1 volta)

```bash
cd /path/to/fly-catcher

# Installa dipendenze
python3.11 -m pip install -r requirements.txt --quiet

# Genera chiave HMAC e salva in .env per la demo
export ADSB_HMAC_KEY=$(python3.11 -c 'import secrets; print(secrets.token_hex(32))')

# Traina modello Isolation Forest su dati reali
python3.11 -m ml.train --samples notebook/samples --augment 200
# Output atteso:
# INFO: Total records: 8486
# INFO: Feature vectors from real data: 8466
# INFO: IF trained on 8666 samples
# INFO: Validation — ghost aircraft score: 0.734

# Verifica test suite (opzionale — buono da mostrare)
python3.11 -m pytest tests/ -q
# Output atteso: 97 passed in X.Xs
```

---

## Cue card video (5 minuti — 6 scene)

---

### SCENA 1 — Avvio pulito (0:00-0:40)

**Cosa fare:**
```bash
# Terminale 1 — avvio sistema
bash demo/start_demo.sh
```

**Cosa mostrare a schermo:**
- Log di avvio con HMAC_KEY generata
- "Pipeline started (interval=3.0s)"
- "Dashboard at http://localhost:5000"

**Cosa dire:**
"ADS-B Secure si avvia con variabili d'ambiente sicure — la chiave HMAC non è mai hardcoded nel codice. La pipeline parte immediatamente: acquisizione dati, validazione strutturale, HMAC PoC, replay detection e anomaly detection sono attivi in sequenza."

---

### SCENA 2 — Dashboard Leaflet.js (0:40-1:20)

**Cosa fare:**
- Apri browser → `http://localhost:5000`
- Login con `operator / operator123`
- Mostra la mappa con i voli correnti (tutti UNVERIFIED o VALID)
- Click su un marker → popup con dettagli (ICAO, altitudine, velocità, anomaly score)

**Cosa mostrare:**
- Mappa scura con marker verdi/arancioni
- Tabella sotto la mappa con colonne: ICAO, Flight, Status, Alt, Speed, Anomaly Score

**Cosa dire:**
"Il controllore di volo vede in tempo reale le tracce ADS-B con il loro stato di sicurezza: verde per VALID, arancione per UNVERIFIED quando HMAC non è verificabile, rosso per SUSPICIOUS. Il sistema distingue immediatamente traffico legittimo da potenziali minacce."

---

### SCENA 3 — Ghost Aircraft / Replay Attack (1:20-2:30)

**Cosa fare (Terminale 2 — mantieni dashboard visibile):**
```bash
# Ghost aircraft con formato invalido (catturato da StructuralValidator)
python3.11 demo/inject_attack.py --attack ghost
```

**Output atteso nel terminale:**
```
ATTACK: Ghost Aircraft Injection (MC1)
Injecting 1 packet(s)...
  [0] INVALID hex=ghost1 reasons=['altitude_out_of_range:99999', 'speed_out_of_range:9999']
Forensic log: 1 events | Chain intact: True
Log events (latest first):
  [LOW] packet_invalid icao=ghost1 id=abcd1234 hash=ef01...
```

```bash
# Replay attack (catturato da ReplayDetector)
python3.11 demo/inject_attack.py --attack replay
```

**Output atteso:**
```
ATTACK: Replay Attack (MC2)
  [0] REPLAY hex=3c4b12 seen=60.0s → SUSPICIOUS | event id=ab12cd34
Forensic log: 1 events | Chain intact: True
  [HIGH] replay_detected icao=3c4b12 id=... hash=...
```

**Cosa dire:**
"Il ghost aircraft con quota 99.999 piedi e velocità 9.999 nodi viene immediatamente bloccato dallo StructuralValidator al primo livello della pipeline. Il replay attack — un pacchetto ritrasmesso 60 secondi dopo la cattura — viene rilevato dal ReplayDetector perché il campo 'seen' supera la finestra temporale di 30 secondi. In entrambi i casi viene generato un evento nel log forense."

---

### SCENA 4 — HMAC Tampering (2:30-3:10)

**Cosa fare:**
```bash
python3.11 demo/inject_attack.py --attack tamper
```

**Output atteso (con HMAC_KEY set):**
```
ATTACK: Altitude Tampering (MC3)
Altitude tampered: 35000ft → 99ft | Original HMAC tag preserved
  [0] HMAC FAIL hex=a835c5 → SUSPICIOUS | event id=...
Forensic log: 1 events | Chain intact: True
  [HIGH] hmac_fail icao=a835c5
```

**Cosa dire:**
"Questo è il controllo HMAC in ambiente PoC: simuliamo un attaccante che modifica l'altitudine del pacchetto da 35.000 a 99 piedi dopo che il tag HMAC è già stato calcolato sull'originale. Il verificatore rileva la discrepanza tramite HMAC-SHA256 con compare_digest — operazione timing-safe — e classifica il pacchetto come SUSPICIOUS con severità HIGH nel log."

---

### SCENA 5 — Isolation Forest (score > 0.7) (3:10-4:00)

**Cosa fare:**
```bash
# Ghost con formato valido — catturato da IF
python3.11 demo/inject_attack.py --attack ghost_valid
```

**Poi mostrare nel terminale 2:**
```bash
python3.11 -c "
from ml.anomaly_detector import AnomalyDetector
detector = AnomalyDetector()
# Ghost aircraft vector: speed=9999, alt=200000, extreme vr, 5° jump
ghost = [9999.0, 200000.0, 99999.0, 720.0, 5.0, 5.0, 99999.0, 8000.0, 7999.0, 0.0]
score, reason = detector.predict(ghost)
print(f'Ghost score: {score:.3f} | Reason: {reason}')
# Normal aircraft
normal = [450.0, 35000.0, 0.0, 180.0, 0.0002, 0.0003, 10.0, 448.0, 2.0, 1.0]
score2, _ = detector.predict(normal)
print(f'Normal score: {score2:.3f}')
"
```

**Output atteso:**
```
Ghost score: 0.734 | Reason: speed_discrepancy=7999kt|speed_too_high=9999kt|...
Normal score: 0.357
```

**Cosa dire:**
"L'Isolation Forest è addestrato su 8.666 vettori di voli legittimi. La traiettoria del ghost aircraft — salto di 5 gradi in 1 secondo, velocità irreale — produce uno score di 0.73, sopra la soglia di 0.7, e viene classificato SUSPICIOUS con motivazione esplicita. Un volo normale ottiene score 0.35. Il modello fornisce spiegabilità tecnica: non solo 'anomalo', ma perché."

---

### SCENA 6 — Log forense + Chain Verify (4:00-5:00)

**Cosa fare:**
- Apri browser → logout → login come `analyst / analyst123`
- Mostra link "Audit Logs" e "Chain Verify" nella navbar
- Naviga a `http://localhost:5000/api/audit/verify`

**Output atteso nel browser:**
```json
{"chain_intact": true, "broken_at_line": null}
```

- Naviga a `http://localhost:5000/api/audit/logs?severity=high`

**Output:**
```json
{
  "count": N,
  "events": [
    {"event_type": "hmac_fail", "severity": "high", "icao": "a835c5", "hash": "...", "prev_hash": "..."},
    {"event_type": "replay_detected", "severity": "high", "icao": "3c4b12", ...}
  ]
}
```

**Cosa dire:**
"L'analista di sicurezza accede ai log forensi con il proprio ruolo elevato. Il sistema implementa hash chaining SHA-256: ogni record contiene l'hash del record precedente. Se qualcuno modificasse o cancellasse un log post-scrittura, la catena si romperebbe e il sistema lo rileva immediatamente. Questo garantisce non-ripudiabilità e supporto forense post-incidente."

---

## Slide di chiusura (30 secondi)

**Cosa dire:**
"ADS-B Secure dimostra come i principi di Progettazione di Software Sicuro — Defense in Depth, Fail-Safe Defaults, Secure by Design — si traducono in un sistema concreto che mitiga le vulnerabilità strutturali del protocollo ADS-B: spoofing, tampering, replay attack e flooding. Il sistema è un PoC accademico che non modifica il protocollo aeronautico reale, ma mostra come un security layer software possa aumentare significativamente la verificabilità e l'affidabilità del monitoraggio del traffico aereo."

---

## Checklist pre-registrazione

- [ ] `ADSB_HMAC_KEY` esportata nel terminale
- [ ] Modello IF trainato (`models/isolation_forest.pkl` esiste)
- [ ] `bash demo/start_demo.sh` avviato e dashboard risponde
- [ ] Browser aperto su `http://localhost:5000`
- [ ] Terminale 2 pronto per inject_attack.py
- [ ] Risoluzione schermo 1920x1080 o simile
- [ ] Font terminale leggibile (min 14pt)
- [ ] Nessun altro processo su porta 5000

## FAQ tecnica per i professori

**Q: HMAC non è ADS-B reale — perché lo usate?**
A: Lo dichiariamo esplicitamente come PoC. ADS-B è broadcast non autenticato — non è modificabile senza cambiare lo standard ICAO. HMAC dimostra come un ground station fidato potrebbe pre-firmare i messaggi prima di inoltrarli alla pipeline di analisi. Questo è il principio di TESLA ridotto al minimo implementabile.

**Q: L'Isolation Forest potrebbe essere evaso?**
A: Sì — un attacco lento e graduale (adversarial spoofing) potrebbe restare sotto la soglia. Questo è documentato come rischio residuo nel threat model. In produzione servirebbe dataset più grande, labeled, con esempi di attacchi noti.

**Q: Perché Flask e non qualcosa di più production-grade?**
A: Flask è il minimo indispensabile per dimostrare RBAC, sessioni e API REST in un contesto accademico. In produzione: nginx reverse proxy, TLS, database per sessioni, rate limiting a livello infrastrutturale.

**Q: Come gestite il rischio Supply Chain (CVE urllib3)?**
A: urllib3 è una dipendenza transitiva di Flask. I CVE identificati con pip-audit sono documentati nel Vault (11_Bugs_and_Fixes). In produzione si userebbe un virtual environment isolato con versioni fixate.
