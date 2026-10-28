# M4 – Backend Integration Test Evidence

- Date: 2026-10-21
- Branch: m4-tuyet-backend
- Scope: API orders, PostgreSQL persistence, readiness, quantity validation.

## 1. Docker environment
- `order-app`: Up (healthy), mapped to 127.0.0.1:8081.
- `order-db`: Up (healthy), image postgres:17-alpine.
- Backend runtime identity: uid=10001(app), gid=10001(app).
- PostgreSQL version: 17.11 (Alpine).

## 2. Create and read order
- POST `/orders` with customer `M4-Persistence-Test`, product `RestartCheck`, quantity `3`.
- Result: HTTP 201 CREATED.
- Created order ID: 11.
- GET `/orders`: HTTP 200 OK; order ID 11 was returned.
- PostgreSQL query confirmed ID 11, quantity 3, status pending.

## 3. Backend restart and persistence
- Command: `docker compose restart order-app`
- After restart, GET `/orders` returned HTTP 200 OK.
- Order ID 11 remained in the API response.
- PostgreSQL query after restart confirmed the same record.
- Result: PASS for persistence across backend-container restart.

## 4. Readiness with healthy database
- Request: GET `/ready`
- Result: HTTP 200 OK
- Body: `{"database":"connected","status":"ready"}`
- Result: PASS while database was healthy.

## 5. Quantity validation
- Quantity 10: HTTP 201 CREATED — PASS.
- Quantity 2147483647: HTTP 201 CREATED — PASS (maximum accepted signed 32-bit integer).
- Quantity 2147483648: HTTP 400 BAD REQUEST — PASS (rejected).
- Quantity 0: HTTP 400 BAD REQUEST — PASS (rejected).
- Invalid quantity requests did not create additional records in the verification query.

## 6. Docker and logs
- `docker compose ps`: both order-app and order-db reported healthy.
- `docker compose logs --tail=40 order-app`: requests to `/orders` and `/ready` were logged.
- The Flask development-server warning appeared in logs; production WSGI deployment was not assessed by this test.

## 7. Database outage and recovery
- Command: `docker compose stop order-db`
- Request: GET `/ready`
- Result while PostgreSQL was stopped: HTTP 503 SERVICE UNAVAILABLE.
- Response: `{"error":"database unreachable","status":"unready"}`
- Command: `docker compose start order-db`
- After PostgreSQL started, GET `/ready` returned HTTP 200 OK.
- Response: `{"database":"connected","status":"ready"}`
- Result: PASS — readiness accurately reflected database disconnection and recovery.

## 8. Persistence across PostgreSQL-container restart
- Command: `docker compose restart order-db`
- Query: `SELECT id, customer_name, product_name, quantity, status FROM orders WHERE id = 11;`
- Result after restart: ID 11, customer `M4-Persistence-Test`, product `RestartCheck`, quantity `3`, status `pending`.
- Result: PASS — the test order remained available after PostgreSQL-container restart.

## 9. Remaining scope limitation
- Nginx -> Flask -> PostgreSQL end-to-end route and Nginx configuration: NOT VERIFIED. The current Compose services are `order-app` and `order-db`; Nginx was not verified as part of this test.

## 10. Backend unit tests — 2026-10-22
- Command: `docker compose exec -T order-app python -m unittest discover -s tests -v`
- Result: 20 tests ran; all 20 passed; exit code 0.
- Coverage reported by the suite includes order creation/read, database failures, health/readiness, malformed JSON, invalid payloads, quantity boundaries, connection/query failures, timeouts, and readiness recovery.
- Result: PASS for the current backend unit-test suite. This is not evidence that the GitHub Actions workflow has completed successfully.

## 11. Runtime database least privilege — 2026-10-22
- Added `ma-nguon/database/002-runtime-role.sql` to create or update the dedicated `orders_app` runtime role.
- Updated the `order-app` Compose environment to use `orders_app`, rather than the bootstrap/admin role `orders`.
- Applied the SQL script successfully to the local database; reapplying it also completed successfully with exit code 0.
- Verified `orders_app` is not a superuser and does not have CREATEDB, CREATEROLE, REPLICATION, or BYPASSRLS privileges.
- Verified table permissions: SELECT=true, INSERT=true, UPDATE=false, DELETE=false.
- Verified sequence permissions: USAGE/SELECT=true for `orders_id_seq`.
- After switching the application to `orders_app`, `/ready` returned HTTP 200 with `{"database":"connected","status":"ready"}`.
- POST `/orders` using the runtime role returned HTTP 201; the created test record (ID 13) was subsequently found in PostgreSQL.
- Existing order records remained readable after the role switch.
- Credential note: `orders-app-dev` is a local/lab-only development password and must not be reused in production.

## 12. Workflow and configuration checks — 2026-10-22
- `docker compose config -q`: completed successfully.
- Python YAML parser loaded `.github/workflows/verify.yml` successfully.
- `git diff --check`: no whitespace errors at the time of the check.
- The workflow was updated to initialize the schema and runtime role before running unit tests with `orders_app`.
- GitHub Actions execution result: NOT VERIFIED in this evidence; a successful local YAML parse does not establish a passing CI run.

## 13. Remaining limitations and follow-up
- Nginx -> Flask -> PostgreSQL end-to-end route and Nginx configuration: NOT VERIFIED.
- Formal API contract approval from the frontend owner and staging/deployment owner: NOT VERIFIED.
- PostgreSQL image digest pinning: NOT COMPLETED; Compose still references `postgres:17-alpine`.
- CI uses PostgreSQL 16 while the local Compose environment was tested on PostgreSQL 17; version alignment has not been verified.
- Production WSGI deployment, production secret management, and production-grade credential rotation: NOT VERIFIED.
- Persistence and outage/recovery checks documented above were run in the local Compose environment; they do not by themselves prove staging behavior.
