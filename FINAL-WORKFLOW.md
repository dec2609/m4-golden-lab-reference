# Selected M4 workflow ? proposed, not an approved release

Contract **m4-contract-1.0 / PROPOSED_REFERENCE_CHANGE**, package commit `5cba5d2e45f946865737dfec5762427e8a7de6e5`; implementation checkpoint `53f18d8b5689a25bc03b647b54eb1a4ba0cd78ef`.

Canonical normative commands: [WORKFLOW](contract-pr-package/docs/m4-contract/WORKFLOW.md). One CLI: `python -B scripts/run_m4_workflow.py --phase source|release --run-dir EXTERNAL_UNIQUE_RUN ...`. No M3 status or literal security PASS input.

| Stage | Actual entrypoint | Input -> output | Acceptance | Owner / observed layer |
|---|---|---|---|---|
| Freeze source | run_m4_workflow.main | clean GitHEAD/raw snapshot -> source-context.json | clean full-history, no fake artifact fields | integration; REAL CLI |
| Source scan | source_security.main/run_scan | source-context -> manifest/raw scope reports + canonical pair | pinned archive/binary/version; both scopes; no findings/errors | Ng?n; actual producer ERROR emitted, scanner success not verified |
| Dependency | dependency_policy.main | measured requirements/policy -> dependency report/pair | actual allowlist and raw input hashes | Tr?m; actual PASS |
| Unit | m4_result_adapter.unit_main | actual pytest/JUnit -> unit report/pair | actual exit0,255passed, matching JUnit/report hashes | shared; actual PASS |
| Build once | artifact_security.main | same frozen Gitcontext -> OCI archive/index/platform/config | one BuildKit invocation, measured raw identities/provenance | Quang; guard BLOCKED, new OCI path contract-tested/static |
| Sign/verify | artifact_security --sign | exact archive + approved private/public key+independent pin -> bundle | actual Cosign and approved trust, no self-pin | Quang; NOT_RUN |
| Image controls | run_m4_controls --candidate/--run-dir -> m4_candidate_controls | signed/provenance-verified same archive/image -> SBOM/Trivy pairs | supported tools/report schemas, CRITICAL-only policy, raw exits/hashes | Tr?m; no candidate scan success |
| Gate | production_gate.main/evaluate_gate | five assessed controls + recomputed digest/registry/Cosign -> schema2 | eight security_approved checks; invalid/ERROR/FAIL blocks | Quang; fixtures + actual source-only CLI rejection |
| Staging/readiness | deploy_staging.main/operate | gate0 + immutable candidate -> lifecycle/logs | isolated project, HTTP200+correct body, real Orders | Quang/Tuy?t; contracts, runtime NOT_RUN |
| Rollback | test_rollback.main(shared deployment CLI) | failed deploy + previous independently approved immutable image | actual command success and restored identity | Quang; contract doubles only, runtime NOT_RUN |
| Console | PR16 release parser/Nginx/frontend | schema2 + per-run URL -> reported evidence | FIXTURE/UNVERIFIED, NOT_RUN preserved; no approval inference | Thu?n;68unit/contract+build, browser NOT_RUN |

Signing precedes image scans because current PR13 requires a signed archive to enter its scanner path. Signing is not policy approval; scan rejection still blocks release. Do not remove that stronger check merely to reorder the chart. Buildx dual OCI exporter/provenance shape still requires real compatible builder verification. A local unpublished commit cannot masquerade as a reachable public Git revision; owners must publish reviewed fixes before remote immutable Git build.

Source phase collects independent controls even when one fails. On this Windows host, Gitleaks ERROR is evidence-valid but security_approved=false; source phase returns1 and downstream is NOT_RUN. It does not fabricate a release-status with zero artifact digest. Actual artifact guard returned2; actual gate rejected source-only context2. No current release PASS JSON exists.

Publication/staging is downstream of a real candidate and gate. Use run-bound versioned URLs and atomic publication; last-reported evidence is not a new candidate. Actual Nginx/browser publication remains NOT_RUN in this experiment. No frontend lifecycle schema/trust change is introduced.
