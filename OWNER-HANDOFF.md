# Exact owner handoff ? one shared contract

All owners: **m4-contract-1.0**, package local commit **`5cba5d2e45f946865737dfec5762427e8a7de6e5`**. Status **PROPOSED_REFERENCE_CHANGE**, not approved team policy. Candidate implementation reference **`53f18d8b5689a25bc03b647b54eb1a4ba0cd78ef`**. After Thu?n publishes/reviewers merge ONE contract-only PR, use its actual reviewed commitSHA everywhere; do not keep independent stale adapter copies.

## Thu?n ? contract PR preparation only

Review [contract-pr-package](contract-pr-package/README.md),22files (docs/schemas/syntheticexamples/tests). No owner runtime files, workflow YAML, patches, tool binaries, logs or private keys are inside. Do not cherry-pick the laboratory implementation commits into this PR. No PR has been created. Existing frontend68/typechecks/build pass but runtime/browser remain not verified.

## Tr?m ? canonical adapter and producer contract first

Target scripts/m4_result_adapter.py::candidate,emit_control,validate_control,_assess_envelope,unit_main; dependency_policy.main; m4_candidate_controls._emit/run_candidate_controls; run_m4_controls.main. Reference [patch](patches/tram.patch) against assembled base only. Implement exact signature from CONTRACT, flat argv, null artifact subject for source controls, raw identity/hash/exit checks, explicit ControlAssessment (never bool), no fixture branch. Keep current provenance/signature checks and CRITICAL-only policy; source report hash and actual policy/manifest hash required. Reuse existing same-run source records without rewriting identity/overwriting output. LF/CRLF parse equivalently; raw hashes differ.

Acceptance: package17conformance, original adapter/policy suites, actual dependency PASS and valid FAIL/ERROR distinctions; actual Syft/Trivy same candidate when runtime available. Missing/wrong/hash/source/run/subject cases blocked. Do not claim real scanners from fixture tests. Coordinate exact API with Ng?n and gate approval field with Quang.

## Quang ? approval, immutable build, CLI/workflow

Target production_gate.evaluate_gate/main (read .security_approved), artifact_security.main, verify_registry.capture_manifest, workflow verify.yml, Makefile and small run_m4_workflow CLI. Reference [patch](patches/quang.patch). One BuildKit candidate, OCI index/platform/config/archive distinct; verify both exports and Git provenance. Signed archive required before current PR13 scan preflight, with approved external pin; signing alone is not release permission. Current self-hosted dispatch is proposed, not existing/provisioned infrastructure. No M3/literalPASS/fixtures/env-only approval.

Acceptance: contract matrices plus actual clean-source CLI sourcephase; later actual Buildx output compatibility, same-candidate sign/scan/gate0; wrong evidence/unsigned/tampered/invalid producer blocked. Staging re-evaluates gate; rollback only previous approved immutable artifact, failures propagate. Current root tests prove contract paths/doubles, not positive runtime. Provide operator approved key/pin/registry/reachable GitSHA; do not invent them.

## Ng?n ? source producer handoff and cache isolation

Target source_security.main/run_scan/install_and_verify_gitleaks/BIN_DIR and source-security tests. Reference [patch](patches/ngan.patch). Emit canonical GITLEAKS with source/run/snapshot, head/dirty/shallow/scopes/rawcodes/toolmetadata. Flat producer argv in envelope; retain scope argv/output separately. Tool cache external (M4_GITLEAKS_TOOL_DIR); archive and executable hashes independent; actual version8.18.4. Finding with raw0 is FAIL; execution failureERROR, no approval. Existing18source unit tests remain in root suite; new actualmain/emitter positive uses scanner double explicitly.

Acceptance: conformance + original source tests, actual Linux pinned scan on clean full-history+worktree, cache corruption and report/hash/context negatives. Current Linux attempt rejected dirty context, not a real clean scan; cache fix runtime rerun pending. Resolve PR15 EOL conflicts semantically preserving current main in workflow/Compose/dependency/gatetest; no full-directory copy or losing other owners' fixes. No owner PR conflict was modified here.

## Tuy?t ? preserve existing API; runtime verification

No backend/Compose/SQL code patch was introduced here. Existing18DB-double tests pass. Fresh isolated PG17 initialization/runtime role/permissions; POST201/GET200; app+DB restart/persistence; DB outage readiness503/recovery200; staging compatibility still require real execution. Do not present doubles as DB proof.

## Shared integration tests and stop condition

Review [shared-tests.patch](patches/shared-tests.patch) as test adaptation/26new regressions, not production input. Each owner runs conformance against their own checkout then original suites; integration lead assembles reviewed owners at frozen actualSHAs and reruns same-candidate positive/negative workflow. Stop only when runtime evidence is real or a concrete remaining blocker is disclosed. Contract-ready != runtime-complete != academic-ready.
