#!/usr/bin/env bash
set -u

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
FRONTEND_DIR="${FRONTEND_DIR:-frontend}"
PYTHON_BIN="${PYTHON_BIN:-venv/bin/python}"

PASS_COUNT=0
FAIL_COUNT=0

pass() {
  echo "PASS: $1"
  PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
  echo "FAIL: $1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

check_http() {
  local method="$1"
  local path="$2"
  local data="${3:-}"
  local expected="${4:-200}"
  local code

  if [[ "$method" == "GET" ]]; then
    code=$(curl -s -o /tmp/check_all_body.txt -w "%{http_code}" "${BASE_URL}${path}")
  else
    code=$(curl -s -o /tmp/check_all_body.txt -w "%{http_code}" \
      -X "$method" "${BASE_URL}${path}" \
      -H "Content-Type: application/json" \
      -d "$data")
  fi

  if [[ "$code" == "$expected" ]]; then
    pass "${method} ${path} -> ${code}"
  else
    fail "${method} ${path} -> got ${code}, expected ${expected}"
    if [[ -f /tmp/check_all_body.txt ]]; then
      echo "  Response:"
      sed -n '1,3p' /tmp/check_all_body.txt | sed 's/^/    /'
    fi
  fi
}

echo "== Forex AI System Health Check =="
echo "BASE_URL=${BASE_URL}"
echo

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required but not installed."
  exit 1
fi

echo "-- Backend reachability --"
ROOT_CODE=$(curl -s -o /tmp/check_all_root.txt -w "%{http_code}" "${BASE_URL}/")
if [[ "$ROOT_CODE" == "000" ]]; then
  fail "Backend not reachable at ${BASE_URL}"
  echo "  Start backend first:"
  echo "    venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
  echo
  echo "== Summary =="
  echo "Passed: ${PASS_COUNT}"
  echo "Failed: ${FAIL_COUNT}"
  exit 1
else
  pass "Backend reachable (${BASE_URL}/ -> ${ROOT_CODE})"
fi

echo "-- API checks --"
check_http GET "/dashboard"
check_http GET "/signals"
check_http GET "/trade-history"
check_http GET "/analytics"
check_http GET "/telegram-logs"
check_http GET "/ai-analysis"
check_http GET "/settings"
check_http POST "/settings" '{"oanda_api_key":"","telegram_bot_token":"","telegram_chat_id":"","risk_percentage":1,"max_daily_loss":3}'
check_http POST "/auth/login" '{"username":"admin","password":"admin"}'

echo
echo "-- WebSocket route check (TestClient) --"
if [[ -x "$PYTHON_BIN" ]]; then
  WS_RESULT=$("$PYTHON_BIN" - <<'PY'
from fastapi.testclient import TestClient
from app.main import app

try:
    c = TestClient(app)
    with c.websocket_connect("/ws/signals") as ws:
        msg = ws.receive_json()
    ok = isinstance(msg, dict) and "type" in msg and "signals" in msg
    print("PASS" if ok else "FAIL")
except Exception:
    print("FAIL")
PY
)
  if [[ "$WS_RESULT" == "PASS" ]]; then
    pass "WS /ws/signals emits expected payload"
  else
    fail "WS /ws/signals check failed"
  fi
else
  fail "Python binary not found at ${PYTHON_BIN}"
fi

echo
echo "-- Frontend structure checks --"
for f in \
  "${FRONTEND_DIR}/src/App.jsx" \
  "${FRONTEND_DIR}/src/main.jsx" \
  "${FRONTEND_DIR}/src/services/api.js" \
  "${FRONTEND_DIR}/src/hooks/useWebSocket.js" \
  "${FRONTEND_DIR}/src/pages/Dashboard.jsx" \
  "${FRONTEND_DIR}/src/pages/Signals.jsx" \
  "${FRONTEND_DIR}/src/pages/Analytics.jsx" \
  "${FRONTEND_DIR}/src/pages/Trades.jsx" \
  "${FRONTEND_DIR}/src/pages/AIAnalysisPage.jsx" \
  "${FRONTEND_DIR}/src/pages/Settings.jsx" \
  "${FRONTEND_DIR}/src/pages/Login.jsx"
do
  if [[ -f "$f" ]]; then
    pass "Found ${f}"
  else
    fail "Missing ${f}"
  fi
done

echo
echo "== Summary =="
echo "Passed: ${PASS_COUNT}"
echo "Failed: ${FAIL_COUNT}"

if [[ "$FAIL_COUNT" -gt 0 ]]; then
  exit 1
fi

exit 0
