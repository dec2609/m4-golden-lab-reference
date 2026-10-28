# M4 canonical contract - m4-contract-1.0

**PROPOSED_FOR_TEAM_REVIEW.** Interface proposal for ONE contract-only PR. Human review/merge is still required. This freezes interfaces, not organizational approval, scanner execution, CI success or a verified release.

## Authority and scope

Source SHAs and experiment provenance are described in [README](README.md#experimental-provenance-and-test-interpretation). The referenced raw evidence remains in the laboratory and is not included in this contract-only PR. Do not place laboratory runtime patches into this PR. Quang, Trâm and Ngân implement the same reviewed version on their owned branches. Preserve Tuyết's API and Thuận's frontend.

The normalized controls are GITLEAKS, DEPENDENCY, UNIT_TEST, SBOM, VULNERABILITY. DIGEST, REGISTRY, COSIGN are three gate-derived checks over measured artifacts and actual verification, not producer-supplied literal PASS. Together these make the eight existing frontend controls. No M3 evidence or environment-only PASS is an input.

## Identity

- `source_commit`: full 40-lowercase-hex Git commit. `source_snapshot`: SHA-256 over sorted tracked in-scope relative paths, NUL, exact file bytes, NUL. Scope: scripts/, tests/, ma-nguon/, .github/, cau-hinh/, Makefile and root docker-compose*.yml/yaml, excluding every /evidence/ path segment. Ignore outputs, caches and docs; reject dirty/untracked in-scope source. Clean full history for Gitleaks. Freeze the measured source for a run.
- `run_id`: `[A-Za-z0-9_-]{1,100}`; external run directory basename must equal it. No overwrite/replay. Copying historical reports does not create a current run.
- SOURCE_EXECUTION context uses contract `reference-1` plus source/run identities. **No archive, image/config/manifest digests.** GITLEAKS, DEPENDENCY, UNIT_TEST use `artifact_subject:null`, `execution_subject:{kind:source,source_commit,source_snapshot}` even after a real candidate is built.
- BUILD_EXECUTION context adds archive path/SHA, immutable image_reference, manifest_digest (OCI index), platform_manifest_digest (linux/amd64 image manifest), config_digest, artifact_subject=index digest, registry_manifest_path=platform bytes, registry_index_path=index bytes, public_key_path, bundle_path. Archive SHA is never interchangeable with OCI/config digests. Both archive/registry outputs must belong to the same build.
- SBOM/VULNERABILITY use `artifact_subject=manifest_digest` and `execution_subject:{kind:artifact,digest:manifest_digest}`. Index/platform/config distinctions remain explicit. Source controls bind to the source used by that candidate, not a fabricated image.

## One emitter API

```python
emit_control(context, run_dir, control, report_path, raw_exit, verdict, tool, command, reason, *, wrapper_exit_code=None, policy_exit_code=None, repository_root=None, dependency_policy_path=None, expected_dependency_policy_sha256=None, scope=None, head_commit=None, dirty=None, shallow=None, raw_exit_codes=None, scanner_integrity=None)
```

The proposed API is demonstrated at `scripts/m4_result_adapter.py` in the experimental candidate; this PR does not implement it on main. `command` is a nonempty flat argv of the actual producer CLI. Multi-scope scanner argv/raw exits remain in Gitleaks run_manifest/source_context; do not put nested argv in command. Keyword metadata is mandatory by control as described in SCHEMA.md. Output is `<stem>-execution.json` first, then `<stem>-result.json`; report bytes are retained unchanged. Both files must exist and agree before consumption. Write via temporary file + replace; a partial pair is invalid, never approval. No overwrite. Additional signed publication/authentication is outside this hash-consistency interface.

## Validity is not approval

`validate_control(...) -> ControlAssessment(evidence_valid, security_approved, policy_verdict, reason)`; invalid data raises ValueError/OSError and the gate maps it to FAIL. `bool(assessment)` raises TypeError, preventing accidental validity-as-approval. Gate must read `.security_approved` explicitly.

| Record | evidence_valid | security_approved |
|---|---|---|
| Consistent PASS + successful execution/raw0 + valid typed report/identity | true | true for that control only |
| Consistent FAIL/findings/policy rejection | true | false |
| Consistent ERROR, including not-started raw null | true | false |
| Missing/malformed/mismatched evidence | false (validation exception) | false |

SUCCESS may carry raw0 or raw1 only; ERROR retains actual nonzero code or null if no process started. Boolean exit codes are invalid. Raw0 with findings is FAIL, never PASS. Unknown statuses, BYPASS and NOT_PASS never approve. Diagnostic or fixture candidate cannot approve release through the actual gate CLI. No fixture run-name/hash/version exception exists.

## Approval and trust

All eight controls must approve for PRODUCTION_GATE=PASS. Signature verification must use an independently approved public-key SHA-256 pin and real Cosign verification of exact archive bytes. A producer's PASS, key copied with evidence, or valid hash is not independent trust. No private key, token or password in evidence/package. Same-host compromise/replay/TOCTOU are residual risks, not solved by JSON hashes.

See [schema](SCHEMA.md), [workflow](WORKFLOW.md), [owners](OWNER-MATRIX.md), [acceptance](ACCEPTANCE.md).
