# Fresh test matrix ? source `53f18d8b5689a25bc03b647b54eb1a4ba0cd78ef`

| Stage | PASS / FAIL / NOT_RUN | Evidence | Blocker / layer |
|---|---|---|---|
| Unit/contract | PASS255/255; package17/17 | evidence/frozen-source-run/unit.junit.xml, unit-report.json, unit-stdout.log; package-checkpoint.log | root actual pytest; fixture/double controls, not full-stack |
| Negative security | PASS contract26new cases + packagevectors; source-only gate exit2 | tests/test_contract_freeze.py; actual-gate-source-only.json/log | actual validator; positive Cosign/scanner in unit tests are doubles |
| Producer -> gate/assessment | PASS dependency/unit; expected BLOCK GitleaksERROR | frozen-source-run/run-summary.json and canonical files; schema-live-results.json | actual source CLI collectors; no all-eight positive candidate |
| Artifact/signature | NOT_RUN positive; expected buildguard2 | actual-build-guard.json/log | RAM1128MiB<1536; approvedkey/pin/registry/source Git reachability absent |
| Workflow | PASS local source phase enforcement, exit1 expected; release NOT_RUN | frozen-source-workflow.log + run-summary.json | no Actions trigger; self-hosted runner proposal, no CI PASS |
| Backend/DB | PASS18selected; DB runtime NOT_RUN | final-backend.json/log | Flask DB doubles only; two unmocked DB tests excluded explicitly |
| Frontend/API | PASS68,2typechecks,productionbuild | final-frontend*,final-typecheck*,final-production-build* | API doubles/SSR/module tests, no browser/proxy |
| Staging/rollback | NOT_RUN runtime; existing contract tests PASS | root JUnit (deployment tests), FINAL-WORKFLOW.md | no gate-approved candidate/previous approved image; Docker500 |
| Portability | PASS LF and CRLF parser with distinct raw hashes | portability/results.json | parser check only; raw source hashes remain byte-sensitive |
| Tools | versions/integrity inventory partial; scans NOT_RUN/failed | inventory-*.json,gitleaks-download.json,tool-execution/* | pinned archive hash verified; Syft exit125/zero report; Trivy/Cosign exit1 daemon500 |

All root tests are tests/ (255 = inherited229 +26 added). First post-adaptation run229, then249/251 during development, final255; these are successive snapshots, never summed. Unscoped pytest first failed collection on missing psycopg; backend tested separately with its existing interpreter/unittest. Package first17 and final17 are repeated same vectors, never34. Final frontend/backend/typechecks/build record final sourceSHA explicitly.

Canonical source workflow command: `python -B scripts/run_m4_workflow.py --phase source --run-dir ../evidence/frozen-source-run`; exit1 because GitleaksERROR. Actual unit subprocess is recorded in run-summary; exit0,255passed. Full exact argv/exit/output hashes: [EXECUTION-LEDGER](EXECUTION-LEDGER.jsonl).
