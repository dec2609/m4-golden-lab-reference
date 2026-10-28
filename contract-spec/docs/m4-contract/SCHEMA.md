# Exact envelope and control requirements

**PROPOSED_FOR_TEAM_REVIEW - m4-contract-1.0**

Schemas: [result](schemas/control-result.schema.json), [execution](schemas/control-execution.schema.json), [frontend v2](schemas/release-status-v2.schema.json). JSON Schema is structural only; the consumer MUST perform cross-file identities/hashes/typed report/policy checks below. Schema-valid is not security-approved. Integers exclude booleans in Python too.

## Required fields

Every result: contract_version=m4-contract-1.0, schema_version="1.0", control_id, source_commit, source_snapshot, run_id, artifact_subject, execution_subject, execution_status=SUCCESS|ERROR, raw_exit_code=int|null, policy_verdict=PASS|FAIL|ERROR, nonempty reason, tool{name,version}, report{path,sha256}|null, execution_path, wrapper_exit_code=int|null, policy_exit_code=int|null.

Every execution: contract_version, source_commit, source_snapshot, run_id, artifact_subject, execution_subject, raw_exit_code, execution_started:boolean, report_sha256|null, tool{name,version}, command:[nonempty string,...], wrapper_exit_code, policy_exit_code. GITLEAKS additionally requires source_context. Tool name/version must match result; UNKNOWN/UNAVAILABLE can describe ERROR, never PASS. `execution_started == (raw_exit_code is not null)`.

Result/execution source, snapshot, run, subject, raw exits, tool and wrapper/policy exits must agree with each other and trusted context. Paths are POSIX relative to run_dir, confined after resolution, no absolute/traversal/symlink escape. Exact execution filename is gitleaks-, dependency-, unit-test-, sbom- or vulnerability-execution.json. Hash raw bytes before parsing; never normalize bytes to match a historical hash.

## Per-control semantics

| Control | Subject | Required report and execution checks |
|---|---|---|
| GITLEAKS | source | JSON list: empty for PASS; findings imply FAIL even raw0. source_context requires scope=FULL_HISTORY_AND_WORKTREE for PASS, head_commit=context SHA, dirty=false, shallow=false, raw_exit_codes=[0,0] typed integers, scanner_integrity metadata. Retain actual archive SHA, executable SHA, actual version and per-scope raw commands/reports in run_manifest.json. Approved pinned archive and extracted binary are checked independently by producer. |
| DEPENDENCY | source | JSON status/reason, manifest, scope=direct, exact package names/versions/approved booleans, violations, policy_sha256 and manifest_sha256. Compare against current measured requirements and allowlist, not producer PASS. Manifest parse error is ERROR or invalid; admission rejection is FAIL. |
| UNIT_TEST | source | passed/failed nonnegative integer counts, passed>0 and failed=0 for PASS, layer=UNIT_CONTRACT, JUnit hash retained by producer; actual pytest code. This does not prove browser/runtime coverage. |
| SBOM | artifact/index | SPDX-2.x, SPDXID=SPDXRef-DOCUMENT, nonempty packages with name. Actual Syft command/version/raw exit and report hash are bound by execution, source and candidate verification. |
| VULNERABILITY | artifact/index | Trivy SchemaVersion=2 integer, ArtifactType=container_image, ArtifactName=immutable image_reference, Metadata.RepoDigests contains same reference, nonempty Results with Target and Vulnerabilities:null or list. Typed Severity/VulnerabilityID. CRITICAL-only rejection remains existing policy. Missing Results or `{}` is invalid. |
| DIGEST | archive/config/layers/source | Gate recomputes archive SHA, OCI index/platform/config/layer blobs and source labels. Docker archive compatibility is legacy diagnostic; canonical builder emits OCI plus provenance. |
| REGISTRY | index/platform/config | Fetch immutable index/platform bytes; check raw SHA and index->platform->config relation. Never trust a literal verification PASS or mutable tag. |
| COSIGN | exact archive bytes | Independently pinned approved key + real verify-blob bundle/archive. No insecure tlog bypass in proposed workflow. Signing attests bytes, not policy approval. |

Report null is permitted only for ERROR, and report_sha256 must be null; a process not started uses raw null. ERROR with a report preserves even malformed raw error output for diagnosis but cannot approve. Optional wrapper/policy exits remain null if absent; never fabricate raw exit0.

## Frontend/lifecycle unchanged

Release status v1 historical parsing remains supported. Version2 has source_commit40, artifact_sha256, image_digest, registry, exactly eight PASS|FAIL controls, PRODUCTION_GATE=PASS|BLOCKED and four deployment fields. Probe and deployment gate PASS|FAIL|NOT_RUN; rollback PASS|FAIL|NOT_REQUIRED. Before deployment all probes/gate NOT_RUN, rollback NOT_REQUIRED. Deployment PASS requires production PASS + probes PASS. Rollback PASS/FAIL only on failed deployment. No new rollback enum or automatic deployment approval.

HTTP evidence remains UNVERIFIED; fixture remains FIXTURE. Payload-declared VERIFIED never upgrades trust. A missing/invalid new response clears prior decision. Per-run evidence URL is authoritative for that run; latest historical response is not the next candidate's decision.

## Portability

UTF-8 JSON/text; parser may accept LF/CRLF policy lines. Raw manifests/reports/source fingerprints remain byte-sensitive. A checkout changing EOL must produce a new fingerprint; do not rewrite source identity. Subprocess uses argv arrays, shell only for controlled container/Bash invocation. Outputs/tool cache outside measured checkout, no source modifications by installation.

Examples are **FIXTURE**, synthetic hashes not backed by reports: useful only for schema examples, deliberately not current executable release inputs. Their hashes cannot pass semantic integrity checks. See [acceptance](ACCEPTANCE.md).
