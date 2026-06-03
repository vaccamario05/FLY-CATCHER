# Current State of Repository — Fly-catcher

## Stack reale (osservato nel codice)

| Componente | Tecnologia | Note |
|---|---|---|
| Linguaggio | Python 3 | No virtual env trovato |
| Display | pygame | TFT screen 3.5" su Raspberry Pi |
| Data source | dump1090 HTTP API | `localhost:8080/data/aircraft.json` |
| ML (notebook) | TensorFlow/Keras + scikit-learn | Solo offline, notebook Jupyter |
| Coordinamento | argparse | CLI args: lat, lon, --piawareip |
| GPS math | custom gpsutils.py | lat/lon → pixel x/y |

## Struttura directory

```
fly-catcher/
├── device-rpi/
│   ├── piawareradar.py     ← ENTRYPOINT principale
│   ├── flightdata.py       ← Data layer (fetch + parse)
│   ├── radar.py            ← Rendering radar (pygame)
│   ├── gpsutils.py         ← Coordinate math
│   └── const_normal.py     ← Costanti display (colori, rect, timing)
├── notebook/
│   ├── Fly_Catcher.ipynb          ← Spoofing detection (offline)
│   ├── CNN_Spoofing_Detector.ipynb← Training del modello CNN
│   ├── Spoofed_Aircraft_Generator.ipynb← Generazione dati sintetici
│   ├── Spoof_Detection.h5         ← Modello Keras pre-addestrato
│   └── samples/                   ← JSON sample data
├── fabrication/                   ← File 3D per case
├── assets/                        ← Immagini, PDF
└── README.md
```

## Moduli analizzati

### piawareradar.py (entrypoint)
- Argparse: lat, lon, --piawareip
- Fetch dati da dump1090 HTTP API
- Loop pygame: aggiorna posizioni ogni `FLIGHTDATAREFRESH` ms
- Click su dot → mostra hex, squawk, flight, lat, lon, alt, speed
- **Nessun security check**
- **Nessun logging**
- **Nessuna autenticazione**

### flightdata.py (data layer)
- `FlightData.refresh()`: urlopen → JSON → lista `AirCraftData`
- `AirCraftData` fields: hex, squawk, flight, lat, lon, seen_pos, altitude, vert_rate, track, rssi, speed, messages, seen, mlat
- `_refresh()`: alternativa offline da file locale
- Hash/eq basati su `hex` (ICAO address)
- **Nessuna validazione strutturale**
- **Nessun CRC check**
- **Input non sanitizzato**

### radar.py (display)
- Gestione "dot" su schermo pygame
- `dot_add`, `dot_remove`, `dot_at_point`, `dot_move_by`
- Scala zoom in/out
- **Solo display — nessuna logica sicurezza**

### gpsutils.py
- `lat_lon_to_x_y`: conversione coordinate → pixel
- Funzione semplice, nessun problema di sicurezza

### const_normal.py
- Costanti: colori, posizioni rect, timing refresh
- `FLIGHTDATAREFRESH` = intervallo refresh dati

## Notebook ML

### Fly_Catcher.ipynb
- Carica `aircraft.json` da file
- Raggruppa messaggi per ICAO hex → `PlaneLog`
- Carica `Spoof_Detection.h5` (CNN Keras)
- Feature vector: alt_baro, gs, track, baro_rate, seen_pos, messages, seen, rssi
- Output: "Spoofed" / "Not Spoofed" con percentuale
- **Modalità completamente offline — non integrata nella pipeline real-time**

## Dipendenze implicite (non c'è requirements.txt)

Derivate dal codice:
- `pygame`
- `urllib.request` (stdlib)
- `json` (stdlib)
- `threading` (stdlib)
- `tensorflow` / `keras` (notebook)
- `scikit-learn` (notebook)
- `numpy` (notebook)

## Punti di extension (hook points per ADS-B Secure)

| Punto | File | Come estendere |
|---|---|---|
| Post-fetch, pre-parse | `flightdata.py:refresh()` | Inserire validation layer prima di `parse_flightdata_json` |
| Post-parse | `flightdata.py:parse_flightdata_json()` | Aggiungere classificazione stato traccia |
| Display dot | `piawareradar.py` loop | Colorare dot in base a stato sicurezza |
| Data URL | `DUMP1090DATAURL` | Simulatore alternativo / middleware |

## Vulnerabilità osservate [SECURITY]

1. **Input non validato**: JSON da dump1090 acettato senza CRC/struttura check
2. **No sanitization**: campi stringa (hex, flight) usati raw in rendering
3. **No rate limiting**: loop accetta qualunque volume di dati
4. **No logging**: nessuna traccia di eventi, anomalie o errori
5. **No auth**: nessun controllo accesso all'interfaccia
6. **URL hardcoded**: `localhost:8080` nel codice sorgente
7. **Debug print attivi**: `print("hii ")`, `print(json_data['aircraft'])` in produzione
8. **No error handling**: se dump1090 è down → crash non gestito
