# D2-A — Production frontend tests

This is a frontend-owned test environment, not the group's approved deployment.
Browser -> Nginx production container -> Flask container -> fresh PostgreSQL volume.
No Vite server, no bind-mounted dist, no happy-path interception.

## Prerequisites and side effects

Docker Engine, existing Node/npm frontend dependencies and Edge are required.
The existing @playwright/test 1.64.1 from D1 is reused; no browser installation.
Builds need network/cache for pinned Node/Nginx bases, npm ci, backend base and PostgreSQL.
Allow at least 3 GiB free before starting. Measured first run had 9.2 GB free and Docker 4 GB RAM.
Building writes images/cache; up creates three test containers, a network and a new named volume.
Only frontend publishes a port: 127.0.0.1:5180 -> 8080. Backend/DB stay inside the project network.
The runner privately reads existing main Compose development settings to supply test DB variables;
it never modifies that file, logs resolved passwords, or uses the old project's volumes.

## Run from repository root

    $d2Run = (python ma-nguon/orderflow/e2e/d2_environment.py init | ConvertFrom-Json).run_dir
    python ma-nguon/orderflow/e2e/d2_environment.py preflight --run-dir $d2Run
    if ($LASTEXITCODE -ne 0) { throw "Stop: preflight failed." }
    python ma-nguon/orderflow/e2e/d2_environment.py build --run-dir $d2Run
    if ($LASTEXITCODE -ne 0) { throw "Stop: build failed; inspect preserved attempts." }
    python ma-nguon/orderflow/e2e/d2_environment.py up --run-dir $d2Run
    if ($LASTEXITCODE -ne 0) { throw "Stop: runtime failed; do not run browser." }
    python ma-nguon/orderflow/e2e/d2_environment.py proxy --run-dir $d2Run
    if ($LASTEXITCODE -ne 0) { throw "Stop: real proxy/DB tests failed." }

New names are generated for every run. Preflight/up refuse existing resources rather than reuse a volume.
Build failures keep attempt logs. The repair-frontend command is only for a startup repair of the
three resources already created by the current run before runtime verification; it rebuilds/recreates
frontend only and does not reset DB. Do not use it to change the image after successful browser tests.
Repeated proxy failures keep previous reports; if any row was already created, use a new run rather
than deleting data to make the initial-empty assertion pass.

## Browser tests

From ma-nguon/orderflow, with the same absolute run path:

    $env:D2_RUN_DIR = $d2Run
    node node_modules/@playwright/test/cli.js test --config e2e/playwright.production.config.ts

One Edge worker, retries 0. Config requires real proxy-results PASS and refuses existing browser output.
Three tests cover UI create/list/detail/reload/new context, invalid no-submit, actual backend stop/start.
The last test invokes only the D2 runner's app-stop/app-start for this run, and restores in finally.
The happy-path test has no routing/mocks. Failure screenshots/traces/HTTP attachments are saved per run.

## DB verification, audit and cleanup

Return to repository root:

    python ma-nguon/orderflow/e2e/d2_environment.py db-verify --run-dir $d2Run
    python ma-nguon/orderflow/e2e/d2_environment.py audit --run-dir $d2Run

db-verify compares actual PostgreSQL rows against browser attachments, including UTC timestamps.
Expected synthetic rows: <run>-api and <run>-browser; invalid UI/API must not create another row.
audit verifies runtime UID101, read-only filesystem, CapEff=0, no-new-privileges and records local image identity.
Raw image IDs/engine RepoDigests do not imply independent registry verification or a trusted release.

Always perform cleanup, including after failures:

    python ma-nguon/orderflow/e2e/d2_environment.py cleanup --run-dir $d2Run

This only stops this project's containers; it never down -v, resets, removes containers, prunes or deletes volumes.
Evidence, named volume, network and images remain. D1 and sandbox states/volume names are compared before/after.
Do not stop an old project to make a port available; choose a new approved port/config and record it.

## Coverage and interpretation

Proxy checks measure static index hash against bytes inside the image, JS/CSS/PNG content types,
missing assets 404, SPA reload, /api prefix stripping, GET/POST/201/body, invalid 400/no-write and Flask 404.
They stop only the D2 DB to get Flask's actual generic JSON 500, restore it and verify rows remain.
They pause only the D2 app to measure actual Nginx 504 after its 15-second read timeout, then unpause in finally.
These are real faults in an isolated test project, not deployment/rollback orchestration.
The browser then stops/starts only the D2 backend to check UI error/5xx (observed 504) and recovery.
No intercepted API responses are used anywhere in the D2 browser suite.

The client adapter still times out after 10s. A POST may commit before a response is lost;
there is no proxy upstream retry and the frontend must not automatically retry writes.
D1 has a separate response-loss test; D2 does not claim new server idempotency guarantees.
Flask's default missing-route response is HTML 404; preserving it is correct, replacing it with SPA HTML 200 is not.

Run frontend regression/typecheck/build separately from ma-nguon/orderflow:

    npm.cmd test
    node node_modules/typescript/bin/tsc --noEmit --module ESNext --moduleResolution Bundler --target ES2022 --lib ES2023,DOM --types node --skipLibCheck e2e/orders.spec.ts e2e/d2.orders.spec.ts e2e/playwright.production.config.ts playwright.config.ts
    npm.cmd run build

npm test writes no historical evidence by default. build writes ignored dist/ and tsbuildinfo.
Do not run test:m3, make down or make verify for this phase.

## Evidence and limitations

Run outputs belong only in bang-chung/m4/orderflow/d2/<run-id>/:
baseline/hash/dirty state, sanitized topology, commands/exits, every build attempt,
base OCI descriptors, runtime/audit, proxy results, browser JSON/traces, DB SELECT,
regression logs, cleanup, REPORT.md and hashes. Do not overwrite D1/M3 or discard failed attempts.

D2-A PASS requires real production image/browser/DB plus proxy/negative/regression checks;
build-only or doubles-only is PARTIAL. The 19/10 backend had no /ready endpoint;
those historical observations do not describe the PR14 M4 backend.

## M4 F2/F3 contract update (22/10/2026)

Run the current final suite only in an isolated integration checkout containing
the reviewed PR14 backend and the current frontend working changes. Do not overwrite
the personal worktree backend or reuse a historical D2 evidence directory.
The full-stack setup remains a separate integration operation, not an npm unit test.

The proxy stage now additionally requires real `/api/ready`200 with connected DB,
503 while its own test DB is stopped, and 200 after recovery. Quantity overflow must
return400 without a write. DB stop/start is scoped to the fresh test project and
retains the existing finally recovery. No new cleanup/removal operation was added.

`playwright.final.config.ts` includes `readiness.spec.ts`. Those two readiness cases
intercept HTTP and are SIMULATED, even when served by real Nginx. The consumer suite
also includes explicitly simulated F1 pre-deployment evidence, while its REAL M4
readiness case checks the actual endpoint without interception. Listing or
typechecking these specs is not browser execution, DB recovery or E2E PASS.
No release gate producer, Cosign/registry, official deployment topology or rollback is verified here.
Main Compose, CI, Makefile, backend and assignment documents are outside frontend ownership.

Nginx reference: https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass
SPA reference: https://nginx.org/en/docs/http/ngx_http_core_module.html#try_files
Build reference: https://docs.docker.com/build/building/multi-stage/
