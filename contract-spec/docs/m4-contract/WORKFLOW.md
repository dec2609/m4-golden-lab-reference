# One proposed M4 execution path

**PROPOSED_FOR_TEAM_REVIEW - m4-contract-1.0. Local equivalent, not CI success.**

```text
clean full-history source -> source-context (no artifact fields)
  -> Gitleaks(history+worktree), dependency policy, actual pytest/JUnit
  -> validate all source controls (ERROR/FAIL blocks build)
  -> one BuildKit build (OCI registry + OCI archive exports)
  -> measure index/platform/config/archive + provenance/source labels
  -> sign exact archive + verify with independently approved key/pin
  -> current PR13 verifies signed candidate/provenance -> Syft + Trivy
  -> canonical eight-control gate -> schema2 release-status.json
  -> staging only on gate0 -> /ready200+JSON and Orders smoke
  -> failure -> previous independently approved immutable artifact rollback
  -> run-bound publication/Nginx -> frontend (HTTP UNVERIFIED)
```

The current PR13 scanner preflight requires an already signed OCI archive. Therefore signing precedes scanning in this proposed executable sequence. This is an integrity step, not release approval; all scan controls are still mandatory before gate/staging. Do not rebuild/relabel between these stages or remove signature/provenance checks to get scans to run.

## Commands

Run in Linux x64 with Python pytest/jsonschema, pinned Gitleaks8.18.4 archive, supported Docker Buildx dual exporter, isolated local registry and approved Syft/Trivy/Cosign versions. Tools/cache/outputs outside clean source. No implicit package installation or resource-guard reduction.

```bash
python -B scripts/run_m4_workflow.py --phase source --run-dir /lab/runs/RUN_ID
# A different, unique run directory for a full release, with operator-provided paths/pin:
python -B scripts/run_m4_workflow.py --phase release --run-dir /lab/runs/RELEASE_RUN_ID   --source-git-context 'https://github.com/ORG/REPO.git#FULL40SHA:ma-nguon/order-app'   --image '127.0.0.1:5000/orderflow:RELEASE_RUN_ID'   --public-key /approved/cosign.pub --private-key /private/cosign.key   --trusted-key-sha256 "$APPROVED_PUBLIC_KEY_SHA256"
```

The Git context revision must equal measured source_commit; local unpublished integration commits cannot be represented as a public remote revision. Do not fabricate SLSA metadata for them. Once owner fixes merge to a frozen reachable commit, build that immutable Git context. Current producer verifies source URI/revision and complete resolved dependencies. Docker/BuildKit version compatibility for exact provenance remains a runtime acceptance item, not a claimed PASS.

Actual stage CLIs:

```bash
python -B scripts/source_security.py --candidate "$RUN/source-context.json" --run-dir "$RUN"
python -B scripts/dependency_policy.py --candidate "$RUN/source-context.json" --run-dir "$RUN"
python -B scripts/m4_result_adapter.py --unit --candidate "$RUN/source-context.json" --run-dir "$RUN"
python -B scripts/artifact_security.py --run-dir "$RUN" --image "$IMAGE" --source-git-context "$IMMUTABLE_GIT_CONTEXT"
python -B scripts/artifact_security.py --sign --candidate "$RUN/candidate.json" --run-dir "$RUN" --private-key "$PRIVATE_KEY" --trusted-key-sha256 "$KEY_PIN"
M4_TRUSTED_PUBLIC_KEY_SHA256="$KEY_PIN" python -B scripts/run_m4_controls.py --candidate "$RUN/candidate.json" --run-dir "$RUN"
python -B scripts/production_gate.py --candidate "$RUN/candidate.json" --run-dir "$RUN" --trusted-key-sha256 "$KEY_PIN"
python -B scripts/deploy_staging.py --candidate "$RUN/candidate.json" --status "$RUN/release-status.json" --trusted-key-sha256 "$KEY_PIN" --project "$ISOLATED_PROJECT" --compose docker-compose.staging.yml --base-url "$LAB_URL"
# only if deployment failed and previous approval is independently available:
python -B scripts/test_rollback.py --candidate "$RUN/candidate.json" --status "$RUN/release-status.json" --trusted-key-sha256 "$KEY_PIN" --project "$ISOLATED_PROJECT" --compose docker-compose.staging.yml --base-url "$LAB_URL" --approved-candidate "$PREVIOUS_CANDIDATE" --approved-status "$PREVIOUS_STATUS"
```

Source preflight ERROR returns nonzero, writes valid ERROR when possible, still collects independent dependency/unit outputs. No artifact context means no fabricated release-status JSON. Build guard requires >=1536MiB measured available RAM and >=5GiB disk. Fresh isolated DB/ports/volumes only. Never down -v/prune shared resources. Missing keys, registry, scanner DB or previous approved image are explicit blockers, not mocked positives.

Gate0 only on eight approved controls. Blocked gate1; invalid input/preflight2. Artifact failures2. Producer wrappers preserve raw scanner exit separately (wrapper 0/1/2 is not scanner exit). No publication of partial evidence as valid. Publish versioned run URLs atomically after schema/identity validation; never treat a last-reported endpoint as a new candidate. Publication/browser serving remains integration work, not changed frontend trust semantics.

Workflow dispatch is an explicit local/self-hosted Linux runner proposal using the same CLI and external run dir. Runner/tool/key/registry provisioning is required. Actions was not triggered; tags/action pins and runner configuration need owner review. Do not copy the experimental workflow into this contract-only PR; Quang implements it after freeze.
