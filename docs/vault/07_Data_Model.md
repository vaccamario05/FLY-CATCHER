# Data Model

## AirCraftData (esteso)

```python
@dataclass
class AirCraftData:
    # --- Campi originali Fly-catcher ---
    hex: str              # ICAO 24-bit address (es. "3c4b12")
    squawk: Optional[str]
    flight: Optional[str]
    lat: Optional[float]
    lon: Optional[float]
    seen_pos: Optional[float]  # secondi da ultimo aggiornamento pos
    altitude: Optional[float]  # feet
    vert_rate: Optional[float] # feet/min
    track: Optional[float]     # gradi 0-360
    rssi: Optional[float]      # dBFS
    speed: Optional[float]     # knots
    messages: Optional[int]    # total Mode S messages
    seen: Optional[float]      # secondi da ultimo messaggio
    mlat: Optional[list]

    # --- Campi aggiunti da ADS-B Secure ---
    status: TraceStatus = TraceStatus.UNVERIFIED
    anomaly_score: Optional[float] = None      # 0.0–1.0 (IF score)
    anomaly_reason: Optional[str] = None       # motivo classificazione
    received_at: float = field(default_factory=time.time)
    hmac_valid: Optional[bool] = None
    replay_detected: bool = False
    structural_valid: bool = True
```

## TraceStatus (enum)

```python
class TraceStatus(Enum):
    VALID = "valid"           # superato tutti i controlli
    SUSPICIOUS = "suspicious" # almeno un controllo fallito
    UNVERIFIED = "unverified" # non verificabile (dati mancanti)
    INVALID = "invalid"       # scartato (malformato)
```

## SecurityEvent (per log forense)

```python
@dataclass
class SecurityEvent:
    id: str                    # UUID
    timestamp: float           # unix timestamp
    event_type: SecurityEventType
    severity: Severity
    icao: Optional[str]        # ICAO associato, se disponibile
    details: dict              # dati specifici dell'evento
    prev_hash: str             # SHA-256 del record precedente
    hash: str                  # SHA-256 di questo record
```

## SecurityEventType (enum)

```python
class SecurityEventType(Enum):
    PACKET_INVALID = "packet_invalid"
    HMAC_FAIL = "hmac_fail"
    REPLAY_DETECTED = "replay_detected"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    ANOMALY_DETECTED = "anomaly_detected"
    LOGIN_FAILED = "login_failed"
    LOGIN_SUCCESS = "login_success"
    LOG_CHAIN_BROKEN = "log_chain_broken"
    PACKET_ACCEPTED = "packet_accepted"
```

## User (auth)

```python
@dataclass
class User:
    username: str
    password_hash: str    # werkzeug PBKDF2-SHA256
    role: UserRole
    last_login: Optional[float]
    session_token: Optional[str]
    session_expires: Optional[float]

class UserRole(Enum):
    OPERATOR = "operator"   # solo view dashboard
    ANALYST = "analyst"     # view + log + export
```

## TraceStore (in-memory)

```python
# dict[icao_hex → list[AirCraftData]]
# mantiene storia messaggi per traccia (max N per ICAO, sliding window)
TraceStore = dict[str, deque[AirCraftData]]
```

## Log record (JSONL su disco)

```json
{
  "id": "uuid-v4",
  "timestamp": 1748908800.123,
  "event_type": "replay_detected",
  "severity": "high",
  "icao": "3c4b12",
  "details": {
    "original_timestamp": 1748908770.0,
    "received_timestamp": 1748908800.0,
    "delta_seconds": 30.123,
    "window_seconds": 30
  },
  "prev_hash": "sha256:abcd...",
  "hash": "sha256:ef01..."
}
```

## Config (da env / config file)

```python
ADSB_HMAC_KEY: str          # da env — mai hardcoded
HMAC_WINDOW_SECONDS: int    # default: 30
RATE_LIMIT_PPS: int         # pacchetti/sec — default: 100
LOG_FILE: str               # default: logs/security_events.jsonl
SESSION_TIMEOUT: int        # default: 1800 (30 min)
DUMP1090_URL: str           # default: http://localhost:8080/data/aircraft.json
REPLAY_FILE: Optional[str]  # per simulatore
```
