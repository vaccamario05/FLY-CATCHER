#!/bin/bash
# ============================================================
# ADS-B Secure — Demo startup script
# Università Parthenope — PSS 2025/2026
# ============================================================

set -e

PYTHON=python3.11
PORT=5000

echo "╔══════════════════════════════════════════════════════════╗"
echo "║      ADS-B Secure — Demo Setup                          ║"
echo "╚══════════════════════════════════════════════════════════╝"

# 1. Check Python
if ! command -v $PYTHON &>/dev/null; then
    echo "[ERROR] $PYTHON not found. Use: python3.11"
    exit 1
fi

# 2. Check dependencies
$PYTHON -c "import flask, sklearn, numpy, joblib" 2>/dev/null || {
    echo "[INSTALL] Installing dependencies..."
    $PYTHON -m pip install -r requirements.txt --quiet
}

# 3. HMAC key
if [ -z "$ADSB_HMAC_KEY" ]; then
    export ADSB_HMAC_KEY=$($PYTHON -c 'import secrets; print(secrets.token_hex(32))')
    echo "[OK] HMAC key generated: ${ADSB_HMAC_KEY:0:16}..."
fi

# IF threshold: lower for demo to ensure ghost detection
export IF_THRESHOLD=0.6

# 4. Train IF model if not present
if [ ! -f "models/isolation_forest.pkl" ]; then
    echo "[TRAIN] Training Isolation Forest on real samples..."
    $PYTHON -m ml.train --samples notebook/samples --augment 200
    echo "[OK] Model trained."
else
    echo "[OK] IF model found at models/isolation_forest.pkl"
fi

# 5. Kill any old instance on port
lsof -ti:$PORT | xargs kill -9 2>/dev/null || true

# 6. Start pipeline + dashboard
echo ""
echo "[START] Pipeline + Dashboard starting..."
echo "        Dashboard: http://localhost:$PORT"
echo "        Login:     operator / operator123"
echo "        Analyst:   analyst  / analyst123"
echo ""
echo "[DEMO ATTACKS — run in another terminal (export ADSB_HMAC_KEY first):]"
echo "  export ADSB_HMAC_KEY=$ADSB_HMAC_KEY"
echo "  export IF_THRESHOLD=0.6"
echo "  python3.11 -m demo.inject_attack --attack ghost"
echo "  python3.11 -m demo.inject_attack --attack ghost_valid"
echo "  python3.11 -m demo.inject_attack --attack replay"
echo "  python3.11 -m demo.inject_attack --attack tamper"
echo "  python3.11 -m demo.inject_attack --attack flood"
echo "  python3.11 -m demo.inject_attack --attack all"
echo ""
echo "Press Ctrl+C to stop."
echo ""

$PYTHON -m adsb_secure \
    --mode simulator \
    --file notebook/samples/testing/sample.json \
    --interval 3 \
    --port $PORT
