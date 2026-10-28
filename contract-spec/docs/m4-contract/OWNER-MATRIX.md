# Implementation ownership after contract review

**PROPOSED_FOR_TEAM_REVIEW - m4-contract-1.0. Every owner must use the SAME contract PR commit SHA; no independently copied stale adapter.**

| Owner | Exact target | Required change | Dependency / acceptance |
|---|---|---|---|
| Trâm | scripts/m4_result_adapter.py::emit_control, validate_control, candidate; dependency_policy.py; m4_candidate_controls.py; run_m4_controls.py | One signature/envelope/assessment; GITLEAKS support; source-only null artifact subject; raw hash and CRLF; same-run producer paths; no production fixture branch | Own canonical adapter first; all conformance vectors plus existing policy/SBOM suites; coordinate API with Ngân/Quang |
| Quang | scripts/production_gate.py::evaluate_gate/main; artifact_security.py; verify_registry.py; deploy_staging.py; test_rollback.py; .github/workflows/verify.yml; Makefile | Explicit security_approved; exact enum; signed OCI index/platform/archive distinctions; current CLI arguments; one build; no M3/literal PASS; gate0-only staging; previous immutable approval rollback | Adapter freeze, supplied approved key/pin/tools and runtime; real positive candidate still required; build/provenance implementation is proposed, not runtime-proven |
| Ngân | scripts/source_security.py::main/run_scan/install_and_verify_gitleaks; tests/test_source_security.py | Pass canonical flat producer argv + source metadata; full history/worktree; cache outside checkout; archive vs executable vs actual version; preserve raw findings/errors | Use Trâm emitter; suite + real Linux scanner; do not copy Quang gate or Trâm adapter into own branch |
| Tuyết | existing app.py/SQL/Compose owned files | Preserve Orders/readiness/bootstrap contracts; verify fresh PG17 role/persistence/recovery, no API redesign | Fresh isolated runtime evidence; no backend runtime patch was needed in this experiment |
| Thuận | contract-only docs/schemas/examples/tests PR; existing frontend | Publish proposal for review; preserve v1/v2, NOT_RUN, FIXTURE/UNVERIFIED; later integrate same SHA, real browser/proxy | 68 frontend tests/typechecks/build do not prove full-stack or release trust |

PR15 EOL conflict resolution remains Ngân's reviewed branch update: keep current main semantic changes in .github/workflows/verify.yml, docker-compose.yml, scripts/dependency_policy.py and tests/test_production_gate.py; preserve source-security semantic fixes. Do not copy whole old PR15 tree. This is not performed here.

Runtime patches are OUTSIDE this PR package. Apply small reviewed owner hunks on own branch, never cherry-pick multi-owner laboratory commits. Do not port test fixtures, fake keys/digests, evidence logs, node_modules junction or local toolcache into runtime paths.
