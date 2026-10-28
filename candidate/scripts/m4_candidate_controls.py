
#!/usr/bin/env python3
"""Fail-closed M4 candidate controls, separate from the legacy runner."""

import hashlib
import json
import os
import platform
import re
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from scripts import run_m4_controls as runner
from scripts.m4_result_adapter import emit_control, load_context

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VULN_POLICY = ROOT / "cau-hinh/m4/vulnerability-policy.json"
DEFAULT_DEP_POLICY = ROOT / "cau-hinh/m4/dependency-policy.yml"


class CandidateArtifactError(ValueError):
    def __init__(self, evidence):
        self.evidence = evidence
        super().__init__(evidence.get("reason", "CANDIDATE_ARTIFACT_INVALID"))


def _sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"JSON_EVIDENCE_INVALID:{path}:{exc}") from exc


def _resolve_candidate_file(base, context, field):
    base = Path(base).resolve()
    relative = Path(context[field])
    resolved = (base / relative).resolve()
    if not resolved.is_relative_to(base):
        raise ValueError(f"CANDIDATE_PATH_ESCAPES_BASE:{field}")
    if not resolved.is_file():
        raise ValueError(f"CANDIDATE_FILE_MISSING:{field}:{relative}")
    return resolved


def _read_archive_blob(archive, digest):
    hex_digest = digest.removeprefix("sha256:")
    wanted = ("blobs", "sha256", hex_digest)
    matches = [
        member for member in archive.getmembers()
        if member.isfile()
        and tuple(PurePosixPath(member.name).parts[-3:]) == wanted
    ]
    if len(matches) != 1:
        raise ValueError(
            f"OCI_ARCHIVE_BLOB_COUNT_INVALID:{digest}:{len(matches)}"
        )

    stream = archive.extractfile(matches[0])
    if stream is None:
        raise ValueError(f"OCI_ARCHIVE_BLOB_UNREADABLE:{digest}")
    data = stream.read()
    actual = hashlib.sha256(data).hexdigest()
    if actual != hex_digest:
        raise ValueError(f"OCI_ARCHIVE_BLOB_HASH_MISMATCH:{digest}")
    return data



def _read_archive_file(archive, basename):
    matches = [
        member for member in archive.getmembers()
        if member.isfile() and PurePosixPath(member.name).name == basename
    ]
    if len(matches) != 1:
        raise ValueError(f"OCI_ARCHIVE_FILE_COUNT_INVALID:{basename}:{len(matches)}")
    stream = archive.extractfile(matches[0])
    if stream is None:
        raise ValueError(f"OCI_ARCHIVE_FILE_UNREADABLE:{basename}")
    return stream.read()


def _verify_slsa_provenance(archive, index, context, evidence):
    descriptors = [
        item for item in index.get("manifests", [])
        if isinstance(item, dict)
        and (item.get("annotations") or {}).get(
            "vnd.docker.reference.type"
        ) == "attestation-manifest"
        and (item.get("annotations") or {}).get(
            "vnd.docker.reference.digest"
        ) == context["platform_manifest_digest"]
    ]
    if len(descriptors) != 1:
        raise ValueError(f"SLSA_ATTESTATION_DESCRIPTOR_COUNT_INVALID:{len(descriptors)}")

    attestation_bytes = _read_archive_blob(archive, descriptors[0].get("digest", ""))
    try:
        attestation_manifest = json.loads(attestation_bytes)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("SLSA_ATTESTATION_MANIFEST_INVALID") from exc

    statements = []
    for layer in attestation_manifest.get("layers", []):
        if layer.get("mediaType") != "application/vnd.in-toto+json":
            continue
        raw = _read_archive_blob(archive, layer.get("digest", ""))
        try:
            statement = json.loads(raw)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("SLSA_STATEMENT_INVALID") from exc
        if statement.get("predicateType") == "https://slsa.dev/provenance/v1":
            statements.append(statement)

    if len(statements) != 1:
        raise ValueError(f"SLSA_STATEMENT_COUNT_INVALID:{len(statements)}")

    statement = statements[0]
    platform_hex = context["platform_manifest_digest"].removeprefix("sha256:")
    subjects = statement.get("subject")
    subject_matches = (
        isinstance(subjects, list)
        and any(
            isinstance(item, dict)
            and isinstance(item.get("digest"), dict)
            and item["digest"].get("sha256") == platform_hex
            for item in subjects
        )
    )
    if not subject_matches:
        raise ValueError("SLSA_SUBJECT_DOES_NOT_MATCH_PLATFORM_MANIFEST")

    predicate = statement.get("predicate") or {}
    build_definition = predicate.get("buildDefinition") or {}
    external = build_definition.get("externalParameters") or {}

    # SLSA v1 stores the remote source revision in configSource.digest.sha1.
    external_config = external.get("configSource") or {}
    external_config_digest = external_config.get("digest") or {}
    external_revision = external_config_digest.get("sha1")
    external_source_uri = external_config.get("uri")

    request = external.get("request") or {}
    root_request = request.get("root") or {}
    root_config = root_request.get("configSource") or {}
    root_config_digest = root_config.get("digest") or {}
    root_revision = root_config_digest.get("sha1")
    root_source_uri = root_config.get("uri")

    request_args = (root_request.get("request") or {}).get("args") or {}
    request_revision = request_args.get("vcs:revision")

    run_details = predicate.get("runDetails") or {}
    metadata = run_details.get("metadata") or {}
    buildkit_metadata = metadata.get("buildkit_metadata") or {}
    vcs = buildkit_metadata.get("vcs") or {}
    legacy_revision = vcs.get("revision")

    expected_revision = context["source_commit"]
    revision_fields = [
        ("external_config_source", external_revision),
        ("root_config_source", root_revision),
        ("request_vcs_revision", request_revision),
        ("legacy_buildkit_vcs", legacy_revision),
    ]
    observed_revisions = [
        (field, value)
        for field, value in revision_fields
        if value is not None
    ]

    if not observed_revisions:
        raise ValueError("SLSA_SOURCE_REVISION_MISSING")
    if any(
        not isinstance(value, str) or value != expected_revision
        for _, value in observed_revisions
    ):
        raise ValueError("SLSA_SOURCE_REVISION_MISMATCH")

    source_revision = (
        external_revision or root_revision or request_revision or legacy_revision
    )

    source_uris = [
        uri for uri in (external_source_uri, root_source_uri)
        if uri is not None
    ]
    if not source_uris or any(
        not isinstance(uri, str) or expected_revision not in uri
        for uri in source_uris
    ):
        raise ValueError("SLSA_SOURCE_URI_MISMATCH")

    resolved_dependencies = build_definition.get("resolvedDependencies")
    if not isinstance(resolved_dependencies, list):
        raise ValueError("SLSA_RESOLVED_DEPENDENCIES_INVALID")

    source_dependency_matches = any(
        isinstance(item, dict)
        and isinstance(item.get("digest"), dict)
        and item["digest"].get("sha1") == expected_revision
        and isinstance(item.get("uri"), str)
        and expected_revision in item["uri"]
        for item in resolved_dependencies
    )

    provenance = {
        "predicate_type": statement.get("predicateType"),
        "subject_platform_manifest_digest": "sha256:" + platform_hex,
        "source_revision": source_revision,
        "external_source_revision": external_revision,
        "root_source_revision": root_revision,
        "request_source_revision": request_revision,
        "legacy_buildkit_source_revision": legacy_revision,
        "source_uri": external_source_uri or root_source_uri,
        "resolved_dependencies_count": len(resolved_dependencies),
        "resolved_source_dependency_matches": source_dependency_matches,
        "buildkit_completeness": metadata.get("buildkit_completeness"),
        "builder": run_details.get("builder"),
    }
    evidence["provenance"] = provenance

    if not source_dependency_matches:
        raise ValueError("SLSA_RESOLVED_SOURCE_DEPENDENCY_MISMATCH")

    completeness = metadata.get("buildkit_completeness")
    if (
        not isinstance(completeness, dict)
        or completeness.get("request") is not True
        or completeness.get("resolvedDependencies") is not True
    ):
        raise ValueError("SLSA_PROVENANCE_INCOMPLETE")

    return provenance


def _verify_candidate_artifacts(context, candidate_path):
    evidence = {
        "status": "ERROR",
        "candidate_path": str(Path(candidate_path).resolve()),
        "run_id": context["run_id"],
        "image_reference": context["image_reference"],
        "index_digest": context["manifest_digest"],
        "platform_manifest_digest": context["platform_manifest_digest"],
        "config_digest": context["config_digest"],
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

    try:
        base = Path(candidate_path).resolve().parent
        archive_path = _resolve_candidate_file(base, context, "archive_path")
        manifest_path = _resolve_candidate_file(
            base, context, "registry_manifest_path"
        )
        public_key_path = _resolve_candidate_file(
            base, context, "public_key_path"
        )
        bundle_path = _resolve_candidate_file(base, context, "bundle_path")

        evidence["paths"] = {
            "archive": str(archive_path),
            "registry_manifest": str(manifest_path),
            "public_key": str(public_key_path),
            "bundle": str(bundle_path),
        }

        archive_sha256 = _sha256_file(archive_path)
        evidence["archive_sha256_actual"] = archive_sha256
        if archive_sha256 != context["archive_sha256"]:
            raise ValueError("CANDIDATE_ARCHIVE_SHA256_MISMATCH")

        # Require an independently configured trust pin; do not self-pin the key
        # from the same candidate handoff.
        key_pin = os.environ.get("M4_TRUSTED_PUBLIC_KEY_SHA256", "").strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", key_pin):
            raise ValueError("TRUSTED_COSIGN_KEY_PIN_MISSING_OR_INVALID")

        public_key_sha256 = _sha256_file(public_key_path)
        evidence["public_key_sha256"] = public_key_sha256
        if public_key_sha256 != key_pin:
            raise ValueError("TRUSTED_COSIGN_PUBLIC_KEY_HASH_MISMATCH")

        # The supplied bundle signs the archive, so use verify-blob rather than
        # cosign verify (which verifies a signed image in a registry).
        cosign_bin = os.environ.get("M4_COSIGN_BIN", "cosign")
        command = [
            cosign_bin, "verify-blob",
            "--key", str(public_key_path),
            "--bundle", str(bundle_path),
        ]
        ignore_tlog = (
            os.environ.get("M4_COSIGN_IGNORE_TLOG", "").strip().lower()
            in {"1", "true", "yes"}
        )
        if ignore_tlog:
            command.append("--insecure-ignore-tlog=true")
        command.append(str(archive_path))
        evidence["transparency_log_verification"] = (
            "SKIPPED_INSECURE_IGNORE_TLOG" if ignore_tlog else "ENABLED"
        )
        evidence["cosign_command"] = command
        verify = runner.run(command)
        started = getattr(verify, "execution_started", True) is not False
        evidence["cosign_raw_exit_code"] = (
            verify.returncode if started else None
        )
        evidence["cosign_stdout"] = verify.stdout
        evidence["cosign_stderr"] = verify.stderr
        if not started or verify.returncode != 0:
            raise ValueError("COSIGN_ARCHIVE_SIGNATURE_VERIFICATION_FAILED")
        evidence["signature_status"] = "PASS"

        manifest_bytes = manifest_path.read_bytes()
        platform_digest_actual = "sha256:" + hashlib.sha256(
            manifest_bytes
        ).hexdigest()
        evidence["platform_manifest_digest_actual"] = platform_digest_actual
        if platform_digest_actual != context["platform_manifest_digest"]:
            raise ValueError("CANDIDATE_PLATFORM_MANIFEST_DIGEST_MISMATCH")

        try:
            platform_manifest = json.loads(manifest_bytes)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"REGISTRY_MANIFEST_JSON_INVALID:{exc}") from exc
        config_descriptor = (
            platform_manifest.get("config")
            if isinstance(platform_manifest, dict) else None
        )
        if not isinstance(config_descriptor, dict):
            raise ValueError("REGISTRY_MANIFEST_CONFIG_MISSING")
        if config_descriptor.get("digest") != context["config_digest"]:
            raise ValueError("REGISTRY_MANIFEST_CONFIG_DIGEST_MISMATCH")

        with tarfile.open(archive_path, mode="r:*") as archive:
            # The archive's root index.json is an OCI-layout wrapper.
            # Its descriptor points to the actual registry image index.
            layout_index_bytes = _read_archive_file(
                archive, "index.json"
            )
            evidence["oci_layout_index_sha256"] = (
                "sha256:" + hashlib.sha256(layout_index_bytes).hexdigest()
            )

            try:
                layout_index = json.loads(layout_index_bytes)
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise ValueError(
                    f"CANDIDATE_OCI_LAYOUT_INDEX_INVALID:{exc}"
                ) from exc

            if not isinstance(layout_index, dict):
                raise ValueError("CANDIDATE_OCI_LAYOUT_INDEX_NOT_OBJECT")

            index_descriptors = [
                item for item in layout_index.get("manifests", [])
                if isinstance(item, dict)
                and item.get("digest") == context["manifest_digest"]
                and item.get("mediaType")
                == "application/vnd.oci.image.index.v1+json"
            ]
            if len(index_descriptors) != 1:
                raise ValueError(
                    f"OCI_INDEX_DESCRIPTOR_COUNT_INVALID:"
                    f"{len(index_descriptors)}"
                )

            # Load the nested index by its digest and verify its blob hash.
            index_bytes = _read_archive_blob(
                archive, context["manifest_digest"]
            )
            index_digest_actual = (
                "sha256:" + hashlib.sha256(index_bytes).hexdigest()
            )
            evidence["index_digest_actual"] = index_digest_actual
            if index_digest_actual != context["manifest_digest"]:
                raise ValueError("CANDIDATE_OCI_INDEX_DIGEST_MISMATCH")

            try:
                index = json.loads(index_bytes)
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise ValueError("CANDIDATE_OCI_INDEX_INVALID") from exc

            if not isinstance(index, dict):
                raise ValueError("CANDIDATE_OCI_INDEX_NOT_OBJECT")

            platform_descriptors = [
                item for item in index.get("manifests", [])
                if isinstance(item, dict)
                and item.get("digest") == context["platform_manifest_digest"]
                and item.get("mediaType")
                == "application/vnd.oci.image.manifest.v1+json"
                and (item.get("platform") or {}).get("os") == "linux"
                and (item.get("platform") or {}).get("architecture") == "amd64"
            ]
            if len(platform_descriptors) != 1:
                raise ValueError(
                    f"OCI_PLATFORM_MANIFEST_COUNT_INVALID:"
                    f"{len(platform_descriptors)}"
                )

            archive_manifest = _read_archive_blob(
                archive, context["platform_manifest_digest"]
            )
            archive_config = _read_archive_blob(
                archive, context["config_digest"]
            )
            if archive_manifest != manifest_bytes:
                raise ValueError("ARCHIVE_REGISTRY_MANIFEST_BYTES_MISMATCH")
            if hashlib.sha256(archive_config).hexdigest() != (
                context["config_digest"].removeprefix("sha256:")
            ):
                raise ValueError("ARCHIVE_CONFIG_DIGEST_MISMATCH")

            _verify_slsa_provenance(archive, index, context, evidence)

        evidence["status"] = "PASS"
        evidence["reason"] = (
            "Archive signature, OCI index, platform manifest, config and "
            "complete SLSA provenance verified."
        )
        return evidence

    except Exception as exc:
        evidence["status"] = "ERROR"
        evidence["reason"] = str(exc)[:1000]
        raise CandidateArtifactError(evidence) from exc

def _emit(context, run_dir, control, report_path, raw_exit, verdict,
          tool, command, reason, wrapper_exit_code=None,
          policy_exit_code=None):
    result_path = Path(run_dir) / f"{control.lower()}-result.json"
    execution_path = Path(run_dir) / f"{control.lower()}-execution.json"

    try:
        emit_control(
            context=context,
            run_dir=run_dir,
            control=control,
            report_path=report_path,
            raw_exit=raw_exit,
            verdict=verdict,
            tool=tool,
            command=command,
            reason=reason,
            wrapper_exit_code=wrapper_exit_code,
            policy_exit_code=policy_exit_code,
            repository_root=ROOT,
        )
        return verdict
    except Exception as exc:
        if result_path.exists() or execution_path.exists():
            print(
                f"{control}_CANONICAL_VALIDATION_ERROR={exc}",
                file=sys.stderr,
            )
            return "ERROR"

        fallback_raw = (
            raw_exit if raw_exit is None or type(raw_exit) is int else None
        )
        try:
            emit_control(
                context=context,
                run_dir=run_dir,
                control=control,
                report_path=(
                    report_path
                    if report_path is not None and Path(report_path).is_file()
                    else None
                ),
                raw_exit=fallback_raw,
                verdict="ERROR",
                tool=tool,
                command=command,
                reason=f"CANONICAL_VALIDATION_ERROR:{exc}",
                wrapper_exit_code=wrapper_exit_code,
                policy_exit_code=policy_exit_code,
                repository_root=ROOT,
            )
        except Exception as fallback_exc:
            print(
                f"{control}_ERROR_RECORD_FAILED={fallback_exc}",
                file=sys.stderr,
            )
        return "ERROR"


def _started(process):
    return getattr(process, "execution_started", True) is not False


def _actual_exit(value):
    return value if type(value) is int else None


def _run_dependency(context, run_dir):
    report_path = Path(run_dir) / "dependency-report.json"
    command = [
        sys.executable,
        str(ROOT / "scripts/dependency_policy.py"),
        "--policy", str(DEFAULT_DEP_POLICY),
        "--output", str(report_path),
    ]
    execution = runner.run(command)
    raw_exit = execution.returncode if _started(execution) else None

    report = None
    if report_path.is_file():
        try:
            report = _read_json(report_path)
        except ValueError:
            report = None

    if (
        raw_exit == 0
        and isinstance(report, dict)
        and report.get("status") == "PASS"
    ):
        verdict = "PASS"
        reason = report.get("reason", "Dependency policy passed.")
    elif (
        raw_exit == 1
        and isinstance(report, dict)
        and report.get("status") == "FAIL"
    ):
        verdict = "FAIL"
        reason = report.get("reason", "Dependency policy failed.")
    else:
        verdict = "ERROR"
        reason = "Dependency execution/report evidence is missing or inconsistent."

    wrapper_code = (
        0 if verdict in {"PASS", "FAIL"} else 2
    )
    tool = {"name": "python", "version": platform.python_version()}

    return _emit(
        context, run_dir, "DEPENDENCY",
        report_path if report_path.is_file() else None,
        raw_exit, verdict, tool, command, str(reason),
        wrapper_exit_code=wrapper_code,
        policy_exit_code=raw_exit,
    )


def _run_sbom(context, run_dir, image, syft_version):
    sbom_dir = Path(run_dir) / "sbom"
    sbom_dir.mkdir(parents=True, exist_ok=True)
    report_path = sbom_dir / "order-app.spdx.json"
    command_wrapper = [
        sys.executable, str(runner.SBOM_SCRIPT),
        "--image", image,
        "--output-dir", str(sbom_dir),
    ]
    wrapper = runner.run(command_wrapper)
    status = runner.get_status(wrapper.stdout, "SBOM_STATUS")
    execution_path = sbom_dir / "syft-execution.json"

    execution = None
    if execution_path.is_file():
        try:
            execution = _read_json(execution_path)
        except ValueError:
            execution = None

    raw_exit = (
        _actual_exit(execution.get("raw_exit_code"))
        if isinstance(execution, dict)
        else None
    )
    report_exists = report_path.is_file()
    report_hash = _sha256_file(report_path) if report_exists else None

    tool = (
        execution.get("tool")
        if isinstance(execution, dict)
        and isinstance(execution.get("tool"), dict)
        else {"name": "syft", "version": syft_version}
    )
    if not isinstance(tool.get("name"), str) or not tool["name"].strip():
        tool["name"] = "syft"
    if not isinstance(tool.get("version"), str) or not tool["version"].strip():
        tool["version"] = syft_version

    command = (
        execution.get("command")
        if isinstance(execution, dict)
        and isinstance(execution.get("command"), list)
        and all(isinstance(item, str) for item in execution["command"])
        else []
    )
    identity_matches = (
        isinstance(execution, dict)
        and execution.get("image_reference") == image
        and execution.get("artifact_subject") == context["manifest_digest"]
        and execution.get("report_sha256") == report_hash
    )

    if (
        _started(wrapper)
        and wrapper.returncode == 0
        and status == "PASS"
        and raw_exit == 0
        and report_exists
        and identity_matches
    ):
        verdict = "PASS"
        reason = "Syft execution, SPDX report hash and candidate subject verified."
        policy_exit = 0
    elif (
        _started(wrapper)
        and wrapper.returncode == 1
        and status == "FAIL"
        and raw_exit is not None
        and report_exists
    ):
        verdict = "FAIL"
        reason = "SBOM control reported a validation failure."
        policy_exit = 1
    else:
        verdict = "ERROR"
        reason = (
            "SBOM process, scanner exit, report hash or candidate subject "
            "could not be verified."
        )
        policy_exit = 2 if wrapper.returncode == 2 else None

    return _emit(
        context, run_dir, "SBOM",
        report_path if report_exists else None,
        raw_exit, verdict, tool, command, reason,
        wrapper_exit_code=wrapper.returncode,
        policy_exit_code=policy_exit,
    )


def _run_vulnerability(context, run_dir, image, trivy_version):
    report_path = Path(run_dir) / "trivy-report.json"
    policy_report = Path(run_dir) / "vulnerability-policy-result.json"
    freshness_report = Path(run_dir) / "trivy-reproducibility-result.json"
    metadata_path = Path.home() / ".cache/trivy/db/metadata.json"

    freshness_command = [
        sys.executable, str(ROOT / "scripts/trivy_reproducibility.py"),
        "--version", trivy_version,
        "--metadata", str(metadata_path),
        "--max-age-hours", "24",
        "--output", str(freshness_report),
    ]
    freshness = runner.run(freshness_command)
    freshness_status = runner.get_status(
        freshness.stdout, "REPRODUCIBILITY_STATUS"
    )
    freshness_reason = runner.get_status(freshness.stdout, "REASON") or (
        "Freshness checker returned no reason."
    )
    runner.write_json(
        Path(run_dir) / "trivy-reproducibility-execution-evidence.json",
        {
            "run_id": context["run_id"],
            "source_commit": context["source_commit"],
            "source_snapshot": context["source_snapshot"],
            "command": freshness_command,
            "raw_exit_code": (
                freshness.returncode if _started(freshness) else None
            ),
            "status": freshness_status or "ERROR",
            "reason": freshness_reason,
            "stdout": freshness.stdout,
            "stderr": freshness.stderr,
            "tool_version": trivy_version,
            "metadata_path": str(metadata_path),
            "result_path": str(freshness_report),
            "result_exists": freshness_report.is_file(),
        },
    )

    trivy_command = [
        "trivy", "image",
        "--format", "json",
        "--output", str(report_path),
        image,
    ]
    trivy = runner.run_trivy_if_fresh(
        trivy_command, freshness, freshness_status, freshness_report
    )
    trivy_started = _started(trivy)
    raw_exit = trivy.returncode if trivy_started else None

    policy = None
    policy_status = None
    policy_reason = "Policy evaluator was not run."
    report_hash = _sha256_file(report_path) if report_path.is_file() else None

    if (
        freshness.returncode == 0
        and freshness_status == "PASS"
        and trivy_started
        and trivy.returncode == 0
        and report_path.is_file()
        and report_hash is not None
    ):
        policy_command = [
            sys.executable, str(runner.VULN_SCRIPT),
            "--report", str(report_path),
            "--policy", str(DEFAULT_VULN_POLICY),
            "--expected-artifact", image,
            "--expected-digest", context["manifest_digest"],
            "--expected-report-sha256", report_hash,
            "--output", str(policy_report),
        ]
        policy = runner.run(policy_command)
        policy_status = runner.get_status(
            policy.stdout, "VULNERABILITY_STATUS"
        )
        policy_reason = runner.get_status(policy.stdout, "REASON") or (
            "Policy evaluator returned no reason."
        )

        runner.write_json(
            Path(run_dir) / "vulnerability-policy-execution-evidence.json",
            {
                "run_id": context["run_id"],
                "source_commit": context["source_commit"],
                "source_snapshot": context["source_snapshot"],
                "command": policy_command,
                "raw_exit_code": (
                    policy.returncode if _started(policy) else None
                ),
                "status": policy_status or "ERROR",
                "stdout": policy.stdout,
                "stderr": policy.stderr,
                "expected_artifact": image,
                "expected_digest": context["manifest_digest"],
                "report_sha256": report_hash,
            },
        )

    if (
        freshness.returncode != 0
        or freshness_status != "PASS"
        or raw_exit != 0
        or not report_path.is_file()
    ):
        verdict = "ERROR"
        reason = (
            "TRIVY_EXECUTION_OR_DATABASE_FRESHNESS_UNVERIFIED: "
            + str(freshness_reason)
        )
    elif (
        policy is not None
        and _started(policy)
        and policy.returncode == 0
        and policy_status == "PASS"
    ):
        verdict = "PASS"
        reason = policy_reason
    elif (
        policy is not None
        and _started(policy)
        and policy.returncode == 1
        and policy_status == "FAIL"
    ):
        verdict = "FAIL"
        reason = policy_reason
    else:
        verdict = "ERROR"
        reason = (
            f"VULNERABILITY_POLICY_EVIDENCE_INVALID: "
            f"status={policy_status!r}; {policy_reason}"
        )

    wrapper_code = (
        0 if raw_exit == 0 and report_path.is_file() else 2
    )
    policy_code = (
        policy.returncode if policy is not None and _started(policy) else None
    )

    return _emit(
        context, run_dir, "VULNERABILITY",
        report_path if report_path.is_file() else None,
        raw_exit, verdict,
        {"name": "trivy", "version": trivy_version},
        trivy_command, reason,
        wrapper_exit_code=wrapper_code,
        policy_exit_code=policy_code,
    )


def run_candidate_controls(args):
    candidate_path = Path(args.candidate).resolve()
    context = load_context(candidate_path, ROOT)

    if args.image and args.image.strip() != context["image_reference"]:
        raise ValueError("CANDIDATE_IMAGE_OVERRIDE_REJECTED")
    if args.run_id and args.run_id != context["run_id"]:
        raise ValueError("CANDIDATE_RUN_ID_OVERRIDE_REJECTED")
    if Path(args.policy).resolve() != DEFAULT_VULN_POLICY.resolve():
        raise ValueError("CANDIDATE_CUSTOM_VULNERABILITY_POLICY_REJECTED")
    if not args.output_dir:
        raise ValueError(
            "CANDIDATE_REQUIRES_EXPLICIT_OUTPUT_DIR_OUTSIDE_CHECKOUT"
        )

    output_root = Path(args.output_dir).resolve()
    if output_root.is_relative_to(ROOT):
        raise ValueError("CANDIDATE_OUTPUT_ROOT_INSIDE_CHECKOUT")

    run_dir = output_root / context["run_id"]
    if run_dir.exists():
        from scripts.m4_result_adapter import read
        prior=read(run_dir/'source-context.json')
        if any(prior.get(k)!=context[k] for k in ('source_commit','source_snapshot','run_id')):
            raise ValueError('SOURCE_RUN_CONTEXT_MISMATCH')
        if any((run_dir/name).exists() for name in ('sbom-result.json','vulnerability-result.json')):
            raise ValueError('REFUSE_OVERWRITE_OR_REPLAYED_IMAGE_SCAN')
    run_dir.mkdir(parents=True, exist_ok=True)

    try:
        candidate_evidence = _verify_candidate_artifacts(
            context, candidate_path
        )
    except CandidateArtifactError as exc:
        runner.write_json(
            run_dir / "candidate-verification-evidence.json",
            exc.evidence,
        )
        print("CANDIDATE_ARTIFACT_STATUS=ERROR")
        print(f"REASON={exc}")
        print(f"RUN_EVIDENCE_DIR={run_dir}")
        return 2

    runner.write_json(
        run_dir / "candidate-verification-evidence.json",
        candidate_evidence,
    )

    image = context["image_reference"]
    syft_version = runner.get_tool_version(["syft", "version"])
    trivy_version = runner.get_tool_version(["trivy", "--version"])

    try:
        identity = runner.inspect_image(image)
        if identity["artifact_subject"] != context["manifest_digest"]:
            raise RuntimeError("DOCKER_SUBJECT_DOES_NOT_MATCH_CANDIDATE")
        if identity["repository_digest"] != image:
            raise RuntimeError("DOCKER_IMMUTABLE_REFERENCE_MISMATCH")
    except Exception as exc:
        reason = f"IMAGE_IDENTITY_ERROR:{exc}"
        sbom_verdict = _emit(
            context, run_dir, "SBOM", None, None, "ERROR",
            {"name": "syft", "version": syft_version},
            [sys.executable, str(ROOT/'scripts/run_m4_controls.py'), '--candidate', str(candidate_path), '--run-dir', str(run_dir)], reason, wrapper_exit_code=2,
        )
        vuln_verdict = _emit(
            context, run_dir, "VULNERABILITY", None, None, "ERROR",
            {"name": "trivy", "version": trivy_version},
            [sys.executable, str(ROOT/'scripts/run_m4_controls.py'), '--candidate', str(candidate_path), '--run-dir', str(run_dir)], reason, wrapper_exit_code=2,
        )
        if (run_dir/'dependency-result.json').exists():
            from scripts.m4_result_adapter import validate_control
            previous=validate_control(run_dir,'DEPENDENCY',context,repository_root=ROOT)
            dep_verdict='PASS' if previous.security_approved else previous.policy_verdict
        else:
            dep_verdict = _run_dependency(context, run_dir)
        print(f"SBOM_VERDICT={sbom_verdict}")
        print(f"VULNERABILITY_VERDICT={vuln_verdict}")
        print(f"DEPENDENCY_VERDICT={dep_verdict}")
        print(f"RUN_EVIDENCE_DIR={run_dir}")
        return 2

    sbom_verdict = _run_sbom(
        context, run_dir, image, syft_version
    )
    vuln_verdict = _run_vulnerability(
        context, run_dir, image, trivy_version
    )
    if (run_dir/'dependency-result.json').exists():
        from scripts.m4_result_adapter import validate_control
        previous=validate_control(run_dir,'DEPENDENCY',context,repository_root=ROOT)
        dep_verdict='PASS' if previous.security_approved else previous.policy_verdict
    else:
        dep_verdict = _run_dependency(context, run_dir)

    verdicts = {
        "SBOM": sbom_verdict,
        "VULNERABILITY": vuln_verdict,
        "DEPENDENCY": dep_verdict,
    }
    for control, verdict in verdicts.items():
        print(f"{control}_VERDICT={verdict}")
        print(f"{control}_RESULT={run_dir / (control.lower() + '-result.json')}")
    print(f"RUN_EVIDENCE_DIR={run_dir}")

    if "ERROR" in verdicts.values():
        return 2
    if "FAIL" in verdicts.values():
        return 1
    return 0
