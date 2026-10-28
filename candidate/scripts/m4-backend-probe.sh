#!/usr/bin/env bash
set -uo pipefail

SCRIPT_PATH="scripts/m4-backend-probe.sh"
REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || exit 2

COMPOSE_PROJECT="${COMPOSE_PROJECT:-n08-m4-tuyet-test}"
APP_BASE_URL="${APP_BASE_URL:-http://127.0.0.1:8081}"
HTTP_TIMEOUT="${HTTP_TIMEOUT:-5}"
EXPECTED_MARKER="${EXPECTED_MARKER:-}"
EVIDENCE_ROOT="${EVIDENCE_ROOT:-bang-chung/m4/backend}"
RUN_ID="${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"

case "$RUN_ID" in
  ""|*[!A-Za-z0-9._-]*)
    echo "Invalid RUN_ID. Use only letters, numbers, dot, underscore or hyphen."
    exit 2
    ;;
esac

case "$HTTP_TIMEOUT" in
  *[!0-9]*|"")
    echo "HTTP_TIMEOUT must be a positive integer."
    exit 2
    ;;
esac

if [ "$HTTP_TIMEOUT" -lt 1 ]; then
  echo "HTTP_TIMEOUT must be at least 1 second."
  exit 2
fi

OUT_DIR="$EVIDENCE_ROOT/$RUN_ID"

if [ -e "$OUT_DIR" ]; then
  echo "Evidence directory already exists; refusing to overwrite: $OUT_DIR"
  exit 2
fi

mkdir -p "$OUT_DIR" || exit 2
REPORT="$OUT_DIR/runtime-probe.txt"
TMP_DIR="$(mktemp -d)" || exit 2
trap 'rm -rf "$TMP_DIR"' EXIT

: > "$REPORT"

log() {
  printf '%s\n' "$*" | tee -a "$REPORT"
}

log "M4 backend runtime probe"
log "Scope: direct backend test endpoint; not production proxy or approved-release identity."
log "Timestamp UTC: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
log "Compose project: $COMPOSE_PROJECT"
log "Base URL: $APP_BASE_URL"
log "HTTP timeout seconds: $HTTP_TIMEOUT"
log "Expected marker configured: $([ -n "$EXPECTED_MARKER" ] && echo yes || echo no)"
log "Source commit: $(git rev-parse HEAD 2>/dev/null || echo UNKNOWN)"
log ""

log "=== Git status ==="
git status --short --branch 2>&1 | tee -a "$REPORT"
log ""
log "=== Tool versions ==="
docker --version 2>&1 | tee -a "$REPORT"
docker compose version 2>&1 | tee -a "$REPORT"
python --version 2>&1 | tee -a "$REPORT"
log ""

log "=== Compose services ==="
docker compose -p "$COMPOSE_PROJECT" ps 2>&1 | tee -a "$REPORT"

log ""
log "=== Test volume ==="
docker volume inspect "${COMPOSE_PROJECT}_order-db-data" \
  --format 'volume={{.Name}}' 2>&1 | tee -a "$REPORT"

log ""
log "=== Runtime identity and permissions ==="
APP_CID="$(docker compose -p "$COMPOSE_PROJECT" ps -q order-app 2>/dev/null || true)"
RUNTIME_OK=0

if [ -n "$APP_CID" ]; then
  log "App configured image and image ID:"
  docker inspect --format 'configured_image={{.Config.Image}} image_id={{.Image}} configured_user={{.Config.User}}' \
    "$APP_CID" 2>&1 | tee -a "$REPORT"

  IDENTITY="$(docker exec "$APP_CID" id 2>/dev/null || true)"
  log "Runtime identity: ${IDENTITY:-UNAVAILABLE}"

  PERMISSIONS="$(docker exec "$APP_CID" sh -c '
    for p in /app /app/app.py /app/tests /app/tests/test_app.py; do
      if test -r "$p"; then r=readable; else r=not-readable; fi
      if test -w "$p"; then w=writable; else w=not-writable; fi
      printf "%s:%s:%s\n" "$p" "$r" "$w"
    done
  ' 2>/dev/null || true)"

  log "File access checks:"
  if [ -n "$PERMISSIONS" ]; then
    printf '%s\n' "$PERMISSIONS" | tee -a "$REPORT"
  else
    log "File access checks unavailable."
  fi

  if [[ "$IDENTITY" == *"uid=10001(app)"* && "$IDENTITY" == *"gid=10001(app)"* ]] &&
     printf '%s\n' "$PERMISSIONS" | grep -Fxq '/app:readable:not-writable' &&
     printf '%s\n' "$PERMISSIONS" | grep -Fxq '/app/app.py:readable:not-writable' &&
     printf '%s\n' "$PERMISSIONS" | grep -Fxq '/app/tests:readable:not-writable' &&
     printf '%s\n' "$PERMISSIONS" | grep -Fxq '/app/tests/test_app.py:readable:not-writable'; then
    RUNTIME_OK=1
    log "Runtime hardening check: PASS"
  else
    log "Runtime hardening check: FAIL or unavailable"
  fi
else
  log "Backend container not found for runtime identity check."
fi

log ""
log "=== HTTP probes ==="

request() {
  local name="$1"
  local path="$2"
  local body_file="$TMP_DIR/${name}.body"
  local err_file="$TMP_DIR/${name}.stderr"
  local status rc

  status="$(curl -sS \
    --connect-timeout 2 \
    --max-time "$HTTP_TIMEOUT" \
    -o "$body_file" \
    -w '%{http_code}' \
    "${APP_BASE_URL}${path}" 2>"$err_file")"
  rc=$?

  printf -v "${name}_STATUS" '%s' "${status:-000}"
  printf -v "${name}_RC" '%s' "$rc"

  log "GET $path: curl_exit=$rc http_status=${status:-000}"
}

json_equals() {
  python - "$1" "$2" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as stream:
        actual = json.load(stream)
    expected = json.loads(sys.argv[2])
except Exception:
    sys.exit(1)

sys.exit(0 if actual == expected else 1)
PY
}

request HEALTH /health
HEALTH_OK=0
if [ "$HEALTH_RC" -eq 0 ] &&
   [ "$HEALTH_STATUS" = "200" ] &&
   json_equals "$TMP_DIR/HEALTH.body" '{"status":"ok"}'; then
  HEALTH_OK=1
  log 'GET /health contract: PASS {"status":"ok"}'
else
  log "GET /health contract: FAIL"
fi

request READY /ready
READY_OK=0
if [ "$READY_RC" -eq 0 ] &&
   [ "$READY_STATUS" = "200" ] &&
   json_equals "$TMP_DIR/READY.body" '{"status":"ready","database":"connected"}'; then
  READY_OK=1
  log 'GET /ready contract: PASS {"status":"ready","database":"connected"}'
else
  log "GET /ready contract: FAIL; response body omitted."
fi

request ORDERS /orders
ORDERS_OK=0
ORDERS_SUMMARY="$(python - "$TMP_DIR/ORDERS.body" "$EXPECTED_MARKER" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as stream:
        payload = json.load(stream)
except Exception:
    print("orders_json=invalid")
    sys.exit(10)

if not isinstance(payload, dict) or not isinstance(payload.get("orders"), list):
    print("orders_schema=invalid")
    sys.exit(10)

orders = payload["orders"]
print(f"orders_count={len(orders)}")

marker = sys.argv[2]
if marker:
    found = any(
        isinstance(order, dict) and order.get("customer_name") == marker
        for order in orders
    )
    print(f"expected_marker_present={'true' if found else 'false'}")
    if not found:
        sys.exit(11)
else:
    print("expected_marker_present=NOT_REQUESTED")
PY
)"
ORDERS_PARSE_RC=$?

if [ "$ORDERS_RC" -eq 0 ] &&
   [ "$ORDERS_STATUS" = "200" ] &&
   [ "$ORDERS_PARSE_RC" -eq 0 ]; then
  ORDERS_OK=1
  log "GET /orders summary: $ORDERS_SUMMARY"
else
  log "GET /orders contract: FAIL; response body omitted."
  log "Orders summary: ${ORDERS_SUMMARY:-unavailable}"
fi

log ""
log "=== Database row-count observation ==="
DB_COUNT="$(docker compose -p "$COMPOSE_PROJECT" exec -T order-db sh -c \
  'PGCONNECT_TIMEOUT=2 psql -U orders -d orders -Atc "SELECT COUNT(*) FROM orders;"' \
  2>/dev/null)"
DB_COUNT_RC=$?

if [ "$DB_COUNT_RC" -eq 0 ]; then
  log "PostgreSQL orders row count: $(printf '%s' "$DB_COUNT" | tr -d '\r\n')"
else
  log "PostgreSQL row-count query: NOT_AVAILABLE (details omitted)"
fi

if [ "$HEALTH_RC" -ne 0 ] || [ "$HEALTH_STATUS" = "000" ]; then
  RESULT="PROCESS_UNREACHABLE"
elif [ "$HEALTH_OK" -ne 1 ]; then
  RESULT="API_ERROR"
elif [ "$READY_STATUS" = "503" ] || [ "$READY_RC" -ne 0 ]; then
  RESULT="DB_UNREADY"
elif [ "$READY_OK" -ne 1 ] || [ "$ORDERS_OK" -ne 1 ]; then
  RESULT="API_ERROR"
elif [ "$RUNTIME_OK" -ne 1 ]; then
  RESULT="RUNTIME_HARDENING_ERROR"
else
  RESULT="PASS"
fi

log ""
log "=== Overall result ==="
log "RESULT=$RESULT"
log "Note: PASS covers this direct-backend probe only; it does not prove production proxy routing or approved release identity."

sha256sum \
  scripts/m4-backend-probe.sh \
  ma-nguon/order-app/app.py \
  ma-nguon/order-app/tests/test_app.py \
  ma-nguon/order-app/Dockerfile \
  docker-compose.yml \
  > "$OUT_DIR/source-files.sha256" || exit 2

(
  cd "$OUT_DIR" &&
  sha256sum runtime-probe.txt source-files.sha256 > SHA256SUMS
) || exit 2

echo
echo "Evidence written to: $OUT_DIR"
echo "Evidence hashes:"
cat "$OUT_DIR/SHA256SUMS"

if [ "$RESULT" = "PASS" ]; then
  exit 0
else
  exit 1
fi