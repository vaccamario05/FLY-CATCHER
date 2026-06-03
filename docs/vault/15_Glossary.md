# Glossary

## Termini ADS-B

| Termine | Definizione |
|---|---|
| **ADS-B** | Automatic Dependent Surveillance-Broadcast. Protocollo aeronautico per trasmissione posizione/velocità/identità aeromobili via radio broadcast 1090 MHz. |
| **ICAO address** | Identificativo univoco a 24 bit di ogni aeromobile (campo `hex`). Esempio: `3c4b12`. |
| **dump1090** | Software open-source che riceve segnali ADS-B via SDR e li espone via HTTP come JSON (`aircraft.json`). |
| **Mode S** | Protocollo radar di sorveglianza, di cui ADS-B è un'estensione. |
| **Squawk** | Codice transponder a 4 cifre ottali (es. `7700` = emergenza). |
| **CRC** | Cyclic Redundancy Check. Checksum incluso nel pacchetto ADS-B per rilevare errori di trasmissione. |
| **SDR** | Software Defined Radio. Hardware radio programmabile via software. Esempi: RTL-SDR, FlightAware Pro Stick. |
| **1090 MHz** | Frequenza radio usata da ADS-B (e Mode S). |
| **Ghost aircraft** | Aeromobile inesistente generato iniettando pacchetti ADS-B falsi. |
| **RSSI** | Received Signal Strength Indicator. Potenza del segnale ricevuto in dBFS. |
| **MLAT** | Multilateration. Tecnica di localizzazione indipendente dal transponder basata su differenza tempi di arrivo. |
| **Squitter** | Trasmissione spontanea (non interrogata) del transponder ADS-B. |
| **vert_rate** | Vertical rate. Velocità di salita/discesa in feet/min. |

## Termini Security

| Termine | Definizione |
|---|---|
| **HMAC** | Hash-based Message Authentication Code. Firma crittografica simmetrica per verificare integrità e autenticità di un messaggio. |
| **HMAC-SHA256** | HMAC calcolato con funzione hash SHA-256. Output: 32 byte. |
| **Pre-shared key** | Chiave condivisa tra mittente e ricevitore prima della comunicazione. |
| **Hash chaining** | Tecnica in cui ogni record include il hash del record precedente, rendendo rilevabile qualsiasi modifica. |
| **Append-only** | Log in cui i record possono solo essere aggiunti, mai modificati o cancellati. |
| **Replay attack** | Attacco in cui un messaggio valido intercettato viene ritrasmesso dopo un intervallo di tempo. |
| **Spoofing** | Falsificazione dell'identità di una sorgente (es. trasmissione di pacchetti ADS-B con ICAO altrui). |
| **Tampering** | Alterazione non autorizzata dei dati (es. modifica dell'altitude in un pacchetto ADS-B). |
| **Repudiation** | Impossibilità di provare chi ha compiuto un'azione. Contrario: non-ripudio. |
| **STRIDE** | Framework di threat modeling: Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege. |
| **RBAC** | Role-Based Access Control. Controllo accessi basato su ruoli. |
| **Fail-safe** | Default sicuro: in caso di dubbio, negare accesso o classificare come sospetto. |
| **Defense in Depth** | Strategia di sicurezza con molteplici livelli di controllo indipendenti. |
| **PBKDF2** | Password-Based Key Derivation Function 2. Algoritmo per hashing sicuro delle password. |
| **Trust Boundary** | Confine tra componenti con diversi livelli di fiducia nel sistema. |
| **PoC** | Proof of Concept. Implementazione dimostrativa, non per produzione reale. |

## Termini ML / Anomaly Detection

| Termine | Definizione |
|---|---|
| **Isolation Forest** | Algoritmo di anomaly detection non supervisionato. Isola anomalie costruendo alberi di isolamento casuali. |
| **Anomaly score** | Punteggio di anomalia (0.0 = normale, 1.0 = molto anomalo). |
| **False Positive** | Evento normale classificato erroneamente come anomalia. |
| **False Negative** | Evento anomalo classificato erroneamente come normale. |
| **Feature vector** | Vettore di caratteristiche numeriche estratte da un messaggio/traccia, input al modello ML. |
| **Feature extraction** | Processo di calcolo di caratteristiche rilevanti (es. delta posizione, velocità) da messaggi consecutivi. |
| **CNN** | Convolutional Neural Network. Rete neurale convoluzionale, usata nel modello `Spoof_Detection.h5`. |

## Acronimi progetto

| Acronimo | Significato |
|---|---|
| **ADS-B** | Automatic Dependent Surveillance-Broadcast |
| **IF** | Isolation Forest |
| **TB1** | Trust Boundary 1 (confine sistema/esterno) |
| **PoC** | Proof of Concept |
| **ICAO** | International Civil Aviation Organization |
| **ADR** | Architecture Decision Record |
| **MC** | Misuse Case |
| **SS** | Security Story |
| **RF** | Requisito Funzionale |
| **RNF** | Requisito Non Funzionale |
