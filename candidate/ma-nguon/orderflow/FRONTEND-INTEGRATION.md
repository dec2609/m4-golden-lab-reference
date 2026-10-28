# OrderFlow frontend integration — Phase B, D1 and D2-A

This file describes consumer safeguards, not an approved producer schema v2.

## Standalone frontend follow-up

The shared quantity validator in `src/config/orders.ts` enforces integers from
1 through 2147483647 in the create form, service input and order responses.
This matches the PostgreSQL INTEGER boundary and PR #14's M4 API contract;
server-side enforcement still belongs to the backend owner.

`tests/integration.test.cjs` is a frontend contract suite using explicit test
fixtures and HTTP/hook doubles. It reads no M4 release evidence, runs no producer
scripts and requires none of PR #12–#15 to be imported. Fixture PASS is not a scan
or release approval.

### F1 v2 consumer contract (22/10/2026)

Aligned with PR12 snapshot `4ddf795`: v2 requires registry reference/digest,
all eight PASS/FAIL security controls and all four deployment fields. Source
commit remains a full 40-character SHA. V1 historical compatibility is unchanged.
Deployment probes/gate accept PASS, FAIL or NOT_RUN; rollback remains only
PASS, FAIL or NOT_REQUIRED. Nothing fills missing fields automatically.

A pre-deploy NOT_RUN gate requires both probes NOT_RUN and rollback NOT_REQUIRED.
It preserves reported production PASS/BLOCKED and renders a neutral "not deployed"
message, never deployment PASS/FAIL or approval. Deployment PASS still requires
production and both probes PASS. Attempted rollback PASS/FAIL requires production
PASS and failed deployment. Failed deployment with a NOT_RUN probe remains invalid
pending agreement on partial execution; the current producer executes both probes.
Two PASS probes never upgrade a reported deployment FAIL.

Fixtures remain FIXTURE, HTTP remains UNVERIFIED, and missing provenance is labelled
MISSING. This does not repair producer evidence validation, trust, rollback execution
or evidence serving. The F1 checks are unit/contract/SSR, not browser E2E. Older
run reports below retain their original source/run scope.

The M4 Node test runner uses `--test-concurrency=1`; tests, typecheck and build
should be run sequentially. This limits test concurrency without claiming a
memory guarantee or browser/backend integration coverage.

- Orders use existing GET `/orders` (200 envelope) and POST `/orders` (201 order).
  Responses are checked at runtime. No endpoint or backend schema was added.
- Requests have a 10-second deadline including JSON body consumption. Switching
  source or leaving a view cancels/invalidates pending results. Aborting a POST
  cannot prove that the backend did not commit: errors say creation is unconfirmed
  and advise refreshing before retrying. No automatic write retries or mock fallback.
- Live is a selected mode. Connectivity is the last observed API result with a
  timestamp, not continuous monitoring. Database readiness defaults NOT CHECKED;
  the consumer checks `/api/ready` separately using the PR14 M4 response contract.
- Mock Empty means an initially empty in-memory store; created records remain
  visible to list/detail until a deliberate scenario reset or page reload.

## Release boundary and B4 status

The UI defaults to explicitly labelled demo fixtures; D3 also supports a selectable
same-origin JSON source without automatic fallback. `validateReleaseStatus` checks
the existing v1 fields and conservative v2 consistency safeguards. A valid payload
is not authenticated evidence and never authorizes deployment from the frontend.

`ReleaseEvidenceSource`, `inspectReleaseEvidence` and `validateReleaseJson` prepare
the read/parse/validate boundary without selecting a URL or trusted producer.
The legacy `inspectReleaseEvidence` remains UNVERIFIED. D3 uses readEvidence in
releaseEvidence.ts to connect the Console to a same-origin source, with cancellation,
10s header/body timeout, 1MiB response bound, JSON/MIME validation and empty/error/retry.
HTTP200 or payload flags can never enable VERIFIED. Trusted producer integration
is still BLOCKED pending Quang's confirmation of:

1. Group approval/versioning of the v2 contract and provenance extensions; semantics
   for partial execution, blocked promotion and stale/unavailable results. F1 handles
   the PR12 pre-deploy NOT_RUN shape without adding rollback enums.
2. Endpoint or artifact-serving mechanism, provenance/trust policy, run ID,
   source commit, timestamps/freshness and index versus platform manifest digest.
3. Registry-query evidence and rollback execution/restored digest/post-restore
   health evidence. Equal payload strings and a rollback PASS enum prove neither.

Tuyet owns `/ready`, database readiness semantics, quantity bounds and main Compose.
D1/D2 used separately authorized disposable test databases without waiting for an
official deployment topology. No `/ready` probe or deployment enum was invented.

## Verification and filesystem effects

- `npm test` / `npm run test:m4`: Node unit/contract tests and React server-rendered
  component checks. Uses declared TypeScript dependency for in-memory compilation;
  no installation, browser, HTTP server, database, Docker or security tools.
  Default execution prints results without writing evidence.
- `npm run test:m4 -- --write-evidence`: same tests, explicitly writes only
  `bang-chung/m4/orderflow/verification.txt`, with exit result and source hashes.
- `npm run build`: writes ignored `dist/` and TypeScript build metadata.
- The legacy `npm run test:m3` script is unchanged and writes historical M3
  verification. Do not use it for this phase; v1 regression checks are in M4 tests.

The Phase B Node suite and build alone do not establish browser/backend/PostgreSQL
E2E. D1 and D2-A have separate measured reports below. Registry verification,
release deployment gates and restored rollback remain outside these frontend tests.

## D1 development E2E — measured baseline

Run d1-20261019T132819Z-1136 passed 19 API/DB checks and 7 Edge browser tests
through Vite /api -> Flask -> PostgreSQL. Evidence is preserved under
bang-chung/m4/orderflow/e2e/d1-20261019T132819Z-1136/; its volume must not be reused
for new test runs. D1 is development topology evidence, not production serving.

## D2-A production frontend — implemented and measured

Dockerfile now uses digest-pinned Node and Nginx base descriptors. The build stage
uses package-lock.json with npm ci, then npm run build. The runtime copies only
dist into Nginx; there is no Node/Vite process and no host dist bind mount.
The allowlisted Docker context excludes root .env, node_modules, evidence and E2E.
Browser configuration is same-origin /api; no DB credentials or runtime backend
localhost URL are compiled into the frontend.

Runtime contract:
- Container listens on 8080 as UID/GID 101:101. Nginx temp directories and PID use
  /tmp. The E2E topology verifies read_only, /tmp tmpfs, cap_drop ALL and
  no-new-privileges. These run options must be copied deliberately into any future
  approved Compose; Dockerfile USER alone does not enforce all of them.
- Backend DNS name is order-app, port 8080. Docker resolver 127.0.0.11 refreshes
  upstream addresses. A different platform/service name requires explicit config
  review; this is not a universal deployment configuration.
- /api/ strips the prefix and proxies method/body/status/content type. Error
  interception and upstream retries are disabled, including for POST.
- /api exactly returns 404; /assets/ missing files return 404. API/assets do not
  use SPA fallback. Browser routes fall back to index.html with no-cache; hashed
  assets use immutable caching and correct MIME types.
- Proxy connect timeout is 2s and read/send timeout 15s; frontend adapter deadline
  remains 10s. A client POST timeout still means unconfirmed, never automatic retry.
- Image healthcheck only checks static index serving, not Flask or DB readiness.
  Readiness is a separate explicit `/api/ready` observation, never inferred from
  this static image healthcheck. The original D2 backend lacked that endpoint.

Run d2a-20261019T154849Z-bea1 measured Edge -> production Nginx -> Flask -> real
PostgreSQL: 22 proxy checks, 3/3 browser tests, exact DB persistence, 37/37 frontend
regression, E2E type-check and host/container production builds passed.
Evidence: bang-chung/m4/orderflow/d2/d2a-20261019T154849Z-bea1/REPORT.md.
The frontend Docker image IDs/engine RepoDigests are recorded with their type;
none is described as independent registry/signature verification.
In this engine, the observed .Id equals BuildKit's OCI index digest, while the
platform manifest and config digests differ. See image-identities.json; never
assume .Id means config or platform manifest without checking descriptor type.

The topology ma-nguon/orderflow/e2e/compose.production.yaml is a frontend-owned
TEST configuration, not the group's approved deployment Compose. It publishes
only 127.0.0.1:5180; Flask and PostgreSQL have no host ports. A new project and
volume are mandatory. Existing main Compose, D1 and sandbox remain untouched.
All three D2 containers were stopped; the new volume/network/image/evidence remain.

## Reproduce and integrate later

### Final D3 consumer and readiness (19/10/2026)

services/releaseEvidence.ts checks expected source/archive/image identity when supplied.
An optional PROPOSED provenance object has run_id/generated_at and optional identity
fields that must match the payload. UTC/future/stale guards use a proposed 24h age
and 60s clock skew; these are consumer safeguards, not approved group policy or
authentication. Missing provenance stays MISSING/UNVERIFIED; schema v1 is unchanged.
VERIFIED is a reserved type with no current verifier or executable upgrade path.

Console accepts only same-origin paths without credentials/query/fragment, clears
old decisions on reload/source changes, never silently substitutes fixtures, and
keeps reported PASS separate from release approval. Public VITE_RELEASE_EVIDENCE_PATH
may configure a build; there is no invented producer URL or secret build argument.

At the historical 19/10 run, services/readiness.ts implemented a PROPOSED mapping, independently
of API connectivity. ReadinessNotice probes only on explicit user action; switching
mode cancels/reset observations. Actual Flask404 means NOT_IMPLEMENTED; simulated
READY/UNREADY unit/SSR cases are labelled, not database evidence.

Final also fixes F16 UTC display, newest-first recent orders, keyboard Enter/Space
navigation and aria-invalid/describedby form errors. Final evidence: 50/50 unit tests,
type/build PASS and 6/6 Edge tests on a freshly built production stack. Three are real
Orders regressions, two use labelled synthetic producer responses, one measures
missing-source and /ready404 through the real proxy. DB comparison remains real.
See bang-chung/m4/orderflow/final-thuan/REPORT.md and M4-THUAN-MASTER-HANDOVER.md.
The final fresh-stack run is d2a-20261019T163058Z-ce95; old D1/D2 volumes were untouched.

For final browser regression, use e2e/playwright.final.config.ts with a NEW D2_RUN_DIR
initialized by d2_environment.py and successful proxy checks. Windows Docker
commands now run through Git Bash (ORDERFLOW_GIT_BASH optional path override) with
MSYS path conversion disabled. Keep every stack stopped and retain volumes afterward.

See e2e/PRODUCTION.md for controlled init/preflight/build/proxy/browser/DB/cleanup
commands. Execution requires Docker/service/data-write permission. No new browser
download or dependency was needed for D2; it reuses the installed D1 Playwright/Edge.

Thuận/Quang should inventory port/DNS naming, base-image update policy, inherited
hardening run options, proxy timeouts and test-only topology before integration.
Tuyết still owns /ready, backend quantity bounds/runtime hardening and main Compose;
Quang owns release schema/producer/trust/gates. These are not prerequisites to
the D2-A result, and the result is not production release approval.

## F2 M4 backend alignment and F3 handover (22/10/2026)

Backend contract reviewed directly at PR14 `f31755ac9ad0ffc940654ca81f4f9cdf917f5cba`:
GET `/orders` returns 200 `{orders:[...]}`; POST `/orders` returns a 201 order,
400 on invalid input and generic JSON500 on database failure. There is no backend
GET `/orders/:id`; the frontend detail adapter deliberately reads the list and
finds the ID. Successful timestamps are UTC; quantity is 1..2147483647.

GET `/health` is liveness only. GET `/ready` returns 200
`{status:"ready",database:"connected"}` or 503
`{status:"unready",error:"database unreachable"}`. The consumer rejects missing
error details on an unready response and contradictory ready/error or
unready/connected responses. Missing route404 stays NOT_IMPLEMENTED, not READY.
Network/timeout/malformed errors stay unconfirmed; a later successful check can
recover. Switching Live/Mock cancels and clears readiness observations.

The UI uses `/api/ready` and `/api/orders`; existing Nginx strips `/api/` and
forwards to `order-app:8080`. It needs no additional root `/health` or `/ready`
location. Orders still clears old rows on refresh/error under its existing policy
and never silently switches to Mock or retries a POST. No Orders behavior changed.

The current final browser suite requires an isolated backend containing PR14;
it now expects real readiness200. The source worktree still contains the baseline
backend, so do not run the M4 suite against it and call its404 a readiness success.
`readiness.spec.ts` uses explicitly intercepted HTTP doubles; `consumer.spec.ts`
separates a real M4 readiness case from simulated F1 evidence. The proxy helper adds
real readiness200/503/recovery and overflow400 checks for a future isolated run.
These edits do not establish runtime PASS. Preserve the 19/10 reports unchanged;
their old /ready404 assertions describe those historical runs only.

New F2/F3 execution records are kept under `evidence/f2f3-20261022-*/`, with commands,
raw exits/logs and source hashes. This frontend evidence is never a release-gate
input. Read its verification report for the measured scope and blocked checks.
