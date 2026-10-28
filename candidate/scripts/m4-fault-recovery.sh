#!/usr/bin/env bash
set -uo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || exit 2

COMPOSE_PROJECT="${COMPOSE_PROJECT:-n08-m4-tuyet-test}"
APP_BASE_URL="${APP_BASE_URL:-http://127.0.0.1:8081}"
HTTP_TIMEOUT="${HTTP_TIMEOUT:-5}"
EXPECTED_MARKER="${EXPECTED_MARKER:-OF-M4-20261020-A03-01}"
RUN_ID="${RUN_ID:-tuyet-$(date -u +%Y%m%dT%H%M%SZ)}"
EVIDENCE_ROOT="${EVIDENCE_ROOT:-bang-chung/m4/backend}"
OUT_DIR="$EVIDENCE_ROOT/fault-recovery-$RUN_ID"

case "$RUN_ID" in
  ""|*[!A-Za-z0-9._-]*)
    echo "Invalid RUN_ID."
    exit 2
    ;;
esac

case "$HTTP_TIMEOUT" in
  ""|*[!0-9]*|0)
    echo "HTTP_TIMEOUT must be a positive integer."
    exit 2
    ;;
esac

if [ -e "$OUT_DIR" ]; then
  echo "Refusing to overwrite existing evidence: $OUT_DIR"
  exit 2
fi

mkdir -p "$OUT_DIR" || exit 2
REPORT="$OUT_DIR/fault-recovery.txt"
TMP_DIR="$(mktemp -d)" || exit 2
DB_RECOVERY_NEEDED=0

log() {
  printf '%s\n' "$*" | tee -a "$REPORT"
}

recover_database() {
  if [ "$DB_RECOVERY_NEEDED" -eq 1 ]; then
    log "Emergency recovery attempt: start order-db"
    docker compose -p "$COMPOSE_PROJECT" start order-db >>"$REPORT" 2>&1 || true

    for i in $(seq 1 30); do
      health="$(docker inspect \
        --format '{{.State.Health.Status}}' \
        "${COMPOSE_PROJECT}-order-db-1" 2>/dev/null || true)"
      log "Recovery wait $i: DB health=${health:-unknown}"

      if [ "$health" = "healthy" ]; then
        DB_RECOVERY_NEEDED=0
        log "Emergency recovery: DB healthy"
        break
      fi
      sleep 2
    done

    if [ "$DB_RECOVERY_NEEDED" -eq 1 ]; then
      log "ERROR: DB did not become healthy automatically. Manual recovery required."
    fi
  fi
}

cleanup() {
  recover_database
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

log "M4 A06 database fault/recovery evidence"
log "Scope: dedicated test Compose project only; not production."
log "UTC: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
log "Project: $COMPOSE_PROJECT"
log "Base URL: $APP_BASE_URL"
log "HTTP timeout seconds: $HTTP_TIMEOUT"
log "Expected marker: $EXPECTED_MARKER"
log "Source commit: $(git rev-parse HEAD 2>/dev/null || echo UNKNOWN)"
log ""

if ! docker compose -p "$COMPOSE_PROJECT" ps order-db | grep -q 'order-db'; then
  log "FAIL: order-db service not found."
  exit 1
fi

if ! docker compose -p "$COMPOSE_PROJECT" ps order-app | grep -q 'order-app'; then
  log "FAIL: order-app service not found."
  exit 1
fi

DB_COUNT_BEFORE="$(docker compose -p "$COMPOSE_PROJECT" exec -T order-db \
  sh -c 'PGCONNECT_TIMEOUT=2 psql -U orders -d orders -Atc "SELECT COUNT(*) FROM orders;"' \
  2>/dev/null)"
DB_COUNT_RC=$?

if [ "$DB_COUNT_RC" -ne 0 ]; then
  log "FAIL: unable to read DB row count before fault."
  exit 1
fi

log "DB row count before fault: $(printf '%s' "$DB_COUNT_BEFORE" | tr -d '\r\n')"
log ""

log "=== Stop dedicated test DB ==="
if docker compose -p "$COMPOSE_PROJECT" stop order-db >>"$REPORT" 2>&1; then
  DB_RECOVERY_NEEDED=1
  log "DB stop: completed"
else
  log "FAIL: could not stop test DB."
  exit 1
fi

sleep 2

request() {
  local name="$1"
  local path="$2"
  local status rc

  status="$(curl -sS \
    --connect-timeout 2 \
    --max-time "$HTTP_TIMEOUT" \
    -o "$TMP_DIR/$name.body" \
    -w '%{http_code}' \
    "${APP_BASE_URL}${path}" 2>"$TMP_DIR/$name.stderr")"
  rc=$?

  printf -v "${name}_STATUS" '%s' "${status:-000}"
  printf -v "${name}_RC" '%s' "$rc"
  log "$name: curl_exit=$rc HTTP=${status:-000}"
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

OUTAGE_OK=1

log ""
log "=== Probes while DB is stopped ==="

request HEALTH /health
if [ "$HEALTH_RC" -eq 0 ] &&
   [ "$HEALTH_STATUS" = "200" ] &&
   json_equals "$TMP_DIR/HEALTH.body" '{"status":"ok"}'; then
  log "Liveness during DB outage: PASS"
else
  log "Liveness during DB outage: FAIL"
  OUTAGE_OK=0
fi

request READY /ready
if [ "$READY_RC" -eq 0 ] &&
   [ "$READY_STATUS" = "503" ] &&
   json_equals "$TMP_DIR/READY.body" '{"error":"database unreachable","status":"unready"}'; then
  log "Readiness during DB outage: PASS (503)"
else
  log "Readiness during DB outage: FAIL"
  OUTAGE_OK=0
fi

request ORDERS /orders
if [ "$ORDERS_RC" -eq 0 ] &&
   [ "$ORDERS_STATUS" = "500" ] &&
   json_equals "$TMP_DIR/ORDERS.body" '{"error":"Internal server error"}'; then
  log "Orders API during DB outage: PASS (500 generic JSON)"
else
  log "Orders API during DB outage: FAIL"
  OUTAGE_OK=0
fi

log ""
log "=== Restore test DB ==="

if docker compose -p "$COMPOSE_PROJECT" start order-db >>"$REPORT" 2>&1; then
  log "DB start: requested"
else
  log "DB start request failed; emergency recovery will retry."
fi

for i in $(seq 1 30); do
  DB_HEALTH="$(docker inspect \
    --format '{{.State.Health.Status}}' \
    "${COMPOSE_PROJECT}-order-db-1" 2>/dev/null || true)"
  log "DB health poll $i: ${DB_HEALTH:-unknown}"

  if [ "$DB_HEALTH" = "healthy" ]; then
    DB_RECOVERY_NEEDED=0
    break
  fi
  sleep 2
done

if [ "${DB_HEALTH:-}" != "healthy" ]; then
  log "FAIL: DB did not return to healthy."
  exit 1
fi

request RECOVERED_READY /ready
if [ "$RECOVERED_READY_RC" -eq 0 ] &&
   [ "$RECOVERED_READY_STATUS" = "200" ] &&
   json_equals "$TMP_DIR/RECOVERED_READY.body" '{"database":"connected","status":"ready"}'; then
  log "Readiness after recovery: PASS"
else
  log "Readiness after recovery: FAIL"
  OUTAGE_OK=0
fi

request RECOVERED_ORDERS /orders
if [ "$RECOVERED_ORDERS_RC" -eq 0 ] &&
   [ "$RECOVERED_ORDERS_STATUS" = "200" ]; then
  if python - "$TMP_DIR/RECOVERED_ORDERS.body" "$EXPECTED_MARKER" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as stream:
        payload = json.load(stream)
    orders = payload["orders"]
    found = any(
        isinstance(order, dict)
        and order.get("customer_name") == sys.argv[2]
        for order in orders
    )
except Exception:
    sys.exit(1)

sys.exit(0 if found else 1)
PY
  then
    log "Order persistence after recovery: PASS (expected marker found)"
  else
    log "Order persistence after recovery: FAIL"
    OUTAGE_OK=0
  fi
else
  log "Order API after recovery: FAIL"
  OUTAGE_OK=0
fi

DB_COUNT_AFTER="$(docker compose -p "$COMPOSE_PROJECT" exec -T order-db \
  sh -c 'PGCONNECT_TIMEOUT=2 psql -U orders -d orders -Atc "SELECT COUNT(*) FROM orders;"' \
  2>/dev/null)"
DB_COUNT_AFTER_RC=$?

if [ "$DB_COUNT_AFTER_RC" -eq 0 ]; then
  log "DB row count after recovery: $(printf '%s' "$DB_COUNT_AFTER" | tr -d '\r\n')"

  if [ "$(printf '%s' "$DB_COUNT_BEFORE" | tr -d '\r\n')" = \
       "$(printf '%s' "$DB_COUNT_AFTER" | tr -d '\r\n')" ]; then
    log "Read-only fault/recovery row-count check: PASS (count unchanged)"
  else
    log "Read-only fault/recovery row-count check: FAIL (count changed during probe)"
    OUTAGE_OK=0
  fi
else
  log "DB row count after recovery: UNAVAILABLE"
  OUTAGE_OK=0
fi

if [ "$OUTAGE_OK" -eq 1 ]; then
  RESULT="PASS"
else
  RESULT="FAIL"
fi

log ""
log "RESULT=$RESULT"
log "Scope: observed runtime fault/recovery in dedicated test project only."

sha256sum \
  scripts/m4-fault-recovery.sh \
  scripts/m4-backend-probe.sh \
  scripts/m4-proxy-double.py \
  ma-nguon/order-app/app.py \
  ma-nguon/order-app/tests/test_app.py \
  ma-nguon/order-app/Dockerfile \
  docker-compose.yml \
  > "$OUT_DIR/source-files.sha256" || exit 2

(
  cd "$OUT_DIR" &&
  sha256sum fault-recovery.txt source-files.sha256 > SHA256SUMS &&
  sha256sum -c SHA256SUMS
) || exit 2

if [ "$RESULT" = "PASS" ]; then
  exit 0
else
  exit 1
fi
