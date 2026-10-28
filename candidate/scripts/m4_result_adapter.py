"""Normalize M4 control results into a fail-closed record format."""

from __future__ import annotations
import tarfile
import shutil

import argparse
import re
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_CONTROLS = {"DEPENDENCY", "SBOM", "VULNERABILITY"}
VALID_EXECUTION_STATUSES = {"SUCCESS", "ERROR", "NOT_RUN"}
VALID_VERDICTS = {"PASS", "FAIL", "ERROR", "NOT_RUN"}


def sha256_file(path: str | Path) -> str:
    """Return SHA-256 of a file's exact bytes."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()



# PROVISIONAL_FOR_LAB: candidate/source/report contract helpers.
# These validators do not prove archive provenance or verify signatures.

def _contract_require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def _contract_hex(value: Any, length: int) -> bool:
    import re
    return (
        isinstance(value, str)
        and re.fullmatch(r"[0-9a-f]{" + str(length) + r"}", value) is not None
        and value != "0" * length
    )


def _contract_digest(value: Any) -> bool:
    import re
    return (
        isinstance(value, str)
        and re.fullmatch(r"sha256:[0-9a-f]{64}", value) is not None
    )


def _contract_in_scope(relative: str) -> bool:
    if not relative or "/evidence/" in f"/{relative}/":
        return False
    if relative.startswith((
        "scripts/", "tests/", "ma-nguon/", ".github/", "cau-hinh/"
    )):
        return True
    if relative == "Makefile":
        return True
    return (
        "/" not in relative
        and relative.startswith("docker-compose")
        and relative.endswith((".yml", ".yaml"))
    )


def checkout_snapshot(root: str | Path) -> str:
    """SHA-256 of sorted tracked in-scope paths and exact working-tree bytes."""
    import hashlib
    import subprocess

    repo = Path(root).resolve()
    try:
        raw_paths = subprocess.check_output(
            ["git", "ls-files", "-z"], cwd=repo
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(f"SOURCE_GIT_LIST_FAILED:{exc}") from exc

    paths = sorted(
        item for item in raw_paths.decode("utf-8").split("\0")
        if item and _contract_in_scope(item)
    )
    _contract_require(bool(paths), "SOURCE_SNAPSHOT_SCOPE_EMPTY")

    digest = hashlib.sha256()
    for relative in paths:
        file_path = repo / relative
        _contract_require(
            file_path.is_file(), f"SOURCE_FILE_MISSING:{relative}"
        )
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update(file_path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()



def producer_checkout_snapshot(root: str | Path) -> str:
    """Hash all in-scope producer files, including non-ignored untracked files."""
    import hashlib
    import subprocess

    repo = Path(root).resolve()
    try:
        tracked = subprocess.check_output(
            ["git", "ls-files", "-z"], cwd=repo
        )
        untracked = subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard", "-z"],
            cwd=repo,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(f"PRODUCER_SOURCE_LIST_FAILED:{exc}") from exc

    paths = sorted({
        item
        for raw in (tracked, untracked)
        for item in raw.decode("utf-8").split("\0")
        if item
        and _contract_in_scope(item)
        and ".before-" not in Path(item).name
    })
    _contract_require(bool(paths), "PRODUCER_SOURCE_SNAPSHOT_SCOPE_EMPTY")

    digest = hashlib.sha256()
    for relative in paths:
        file_path = repo / relative
        _contract_require(
            file_path.is_file(),
            f"PRODUCER_SOURCE_FILE_MISSING:{relative}",
        )
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update(file_path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def git_commit_snapshot(root: str | Path, commit: str) -> str:
    """Hash the in-scope file contents recorded in an immutable Git commit."""
    import subprocess

    repo = Path(root).resolve()
    try:
        subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=repo, check=True, capture_output=True,
        )
        raw = subprocess.check_output(
            ["git", "ls-tree", "-r", "-z", commit], cwd=repo
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(f"SOURCE_COMMIT_UNAVAILABLE:{commit}") from exc

    entries = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            fields = metadata.decode("ascii").split()
            relative = raw_path.decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError("SOURCE_COMMIT_TREE_INVALID") from exc
        if len(fields) != 3:
            raise ValueError("SOURCE_COMMIT_TREE_INVALID")
        _mode, kind, oid = fields
        if kind == "blob" and _contract_in_scope(relative):
            entries.append((relative, oid))

    entries.sort(key=lambda item: item[0])
    _contract_require(bool(entries), "SOURCE_SNAPSHOT_SCOPE_EMPTY")

    digest = hashlib.sha256()
    for relative, oid in entries:
        try:
            content = subprocess.check_output(
                ["git", "cat-file", "blob", oid], cwd=repo
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ValueError(f"SOURCE_BLOB_UNAVAILABLE:{relative}") from exc
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update(content)
        digest.update(b"\0")
    return digest.hexdigest()


def candidate(value: Any) -> dict[str, Any]:
    """Validate reference-1 candidate fields and distinguish OCI index from platform manifest."""
    import re

    _contract_require(isinstance(value, dict), "CANDIDATE_NOT_OBJECT")
    _contract_require(
        value.get("contract") == "reference-1",
        "CANDIDATE_CONTRACT_INVALID",
    )
    _contract_require(
        _contract_hex(value.get("source_commit"), 40),
        "SOURCE_COMMIT_INVALID",
    )
    _contract_require(
        _contract_hex(value.get("source_snapshot"), 64),
        "SOURCE_SNAPSHOT_INVALID",
    )
    _contract_require(
        isinstance(value.get("run_id"), str)
        and re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value["run_id"]) is not None,
        "RUN_ID_INVALID",
    )
    _contract_require(
        _contract_hex(value.get("archive_sha256"), 64),
        "ARCHIVE_SHA256_INVALID",
    )
    # manifest_digest is the OCI index digest used by the immutable image reference.
    _contract_require(
        _contract_digest(value.get("manifest_digest")),
        "MANIFEST_DIGEST_INVALID",
    )
    # platform_manifest_digest identifies the linux/amd64 manifest containing config.
    _contract_require(
        _contract_digest(value.get("platform_manifest_digest")),
        "PLATFORM_MANIFEST_DIGEST_INVALID",
    )
    _contract_require(
        _contract_digest(value.get("config_digest")),
        "CONFIG_DIGEST_INVALID",
    )
    _contract_require(
        value.get("artifact_subject") == value.get("manifest_digest"),
        "ARTIFACT_SUBJECT_MISMATCH",
    )

    image_reference = value.get("image_reference")
    _contract_require(
        isinstance(image_reference, str)
        and not any(char.isspace() for char in image_reference)
        and "@" in image_reference
        and image_reference.endswith("@" + value["manifest_digest"])
        and bool(image_reference.rsplit("@", 1)[0]),
        "IMAGE_REFERENCE_NOT_IMMUTABLE",
    )

    for field in (
        "archive_path",
        "registry_manifest_path",
        "public_key_path",
        "bundle_path",
    ):
        relative = value.get(field)
        _contract_require(
            isinstance(relative, str)
            and bool(relative)
            and "\\" not in relative
            and not relative.startswith("/")
            and not re.match(r"^[A-Za-z]:", relative)
            and ".." not in Path(relative).parts
            and Path(relative).as_posix() == relative,
            f"CANDIDATE_PATH_INVALID:{field}",
        )
    producer_commit = value.get("producer_commit")
    producer_snapshot = value.get("producer_snapshot")
    _contract_require(
        (
            producer_commit is None
            and producer_snapshot is None
        )
        or (
            _contract_hex(producer_commit, 40)
            and _contract_hex(producer_snapshot, 64)
        ),
        "PRODUCER_CONTEXT_INVALID",
    )
    return value


def load_context(
    candidate_path: str | Path,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Validate the source snapshot against the declared source commit."""
    import subprocess

    repo = Path(root or Path(__file__).resolve().parents[1]).resolve()
    try:
        value = json.loads(
            Path(candidate_path).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"CANDIDATE_JSON_INVALID:{exc}") from exc

    context = candidate(value)
    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(f"SOURCE_HEAD_UNAVAILABLE:{exc}") from exc

    if context["source_commit"] == head:
        actual_snapshot = checkout_snapshot(repo)
        _contract_require(
            context["source_snapshot"] == actual_snapshot,
            "PRODUCER_SOURCE_SNAPSHOT_MISMATCH",
        )
        _contract_check_untracked_scope(repo)
    else:
        actual_snapshot = git_commit_snapshot(repo, context["source_commit"])
        _contract_require(
            context["source_snapshot"] == actual_snapshot,
            "PRODUCER_SOURCE_SNAPSHOT_MISMATCH",
        )
    return context

def validate_spdx(report: Any) -> None:
    """Validate minimum SPDX structure required by the M4 handoff."""
    _contract_require(isinstance(report, dict), "SPDX_NOT_OBJECT")
    _contract_require(
        report.get("spdxVersion") in ("SPDX-2.2", "SPDX-2.3"),
        "SPDX_VERSION_INVALID",
    )
    _contract_require(
        report.get("SPDXID") == "SPDXRef-DOCUMENT",
        "SPDX_DOCUMENT_ID_INVALID",
    )
    packages = report.get("packages")
    _contract_require(
        isinstance(packages, list) and bool(packages),
        "SPDX_PACKAGES_EMPTY_OR_INVALID",
    )
    _contract_require(
        all(
            isinstance(item, dict)
            and isinstance(item.get("name"), str)
            and bool(item["name"].strip())
            for item in packages
        ),
        "SPDX_PACKAGE_NAME_INVALID",
    )


def validate_trivy(report: Any, context: dict[str, Any]) -> bool:
    """Validate typed Trivy targets and return True only when no CRITICAL exists."""
    _contract_require(isinstance(report, dict), "TRIVY_REPORT_NOT_OBJECT")
    _contract_require(
        type(report.get("SchemaVersion")) is int
        and report["SchemaVersion"] == 2,
        "TRIVY_SCHEMA_VERSION_INVALID",
    )
    _contract_require(
        report.get("ArtifactType") == "container_image",
        "TRIVY_ARTIFACT_TYPE_INVALID",
    )
    _contract_require(
        report.get("ArtifactName") == context["image_reference"],
        "TRIVY_ARTIFACT_NAME_MISMATCH",
    )

    metadata = report.get("Metadata")
    _contract_require(
        isinstance(metadata, dict)
        and isinstance(metadata.get("RepoDigests"), list)
        and context["image_reference"] in metadata["RepoDigests"],
        "TRIVY_REPO_DIGEST_MISMATCH",
    )

    results = report.get("Results")
    _contract_require(
        isinstance(results, list) and bool(results),
        "TRIVY_RESULTS_EMPTY_OR_INVALID",
    )

    allowed = {"UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL"}
    critical_found = False
    for index, result in enumerate(results):
        _contract_require(
            isinstance(result, dict)
            and isinstance(result.get("Target"), str)
            and bool(result["Target"].strip()),
            f"TRIVY_TARGET_INVALID:{index}",
        )
        vulnerabilities = result.get("Vulnerabilities")
        _contract_require(
            "Vulnerabilities" in result
            and (
                vulnerabilities is None
                or isinstance(vulnerabilities, list)
            ),
            f"TRIVY_VULNERABILITIES_INVALID:{index}",
        )
        for vuln_index, vuln in enumerate(vulnerabilities or []):
            _contract_require(
                isinstance(vuln, dict)
                and vuln.get("Severity") in allowed
                and isinstance(vuln.get("VulnerabilityID"), str)
                and bool(vuln["VulnerabilityID"].strip()),
                f"TRIVY_VULNERABILITY_INVALID:{index}:{vuln_index}",
            )
            critical_found = critical_found or vuln["Severity"] == "CRITICAL"

    return not critical_found





def _contract_check_untracked_scope(repo: str | Path) -> None:
    """Reject untracked source files omitted from the tracked-file snapshot."""
    import subprocess

    root = Path(repo).resolve()
    try:
        raw_paths = subprocess.check_output(
            [
                "git", "ls-files", "--others",
                "--exclude-standard", "-z",
            ],
            cwd=root,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(f"SOURCE_UNTRACKED_CHECK_FAILED:{exc}") from exc

    paths = [
        item for item in raw_paths.decode("utf-8").split("\0")
        if item
        and _contract_in_scope(item)
        and ".before-" not in Path(item).name
    ]
    _contract_require(
        not paths,
        "SOURCE_UNTRACKED_IN_SCOPE:" + ",".join(sorted(paths)[:30]),
    )


def _contract_check_current_context(
    context: dict[str, Any], repo: Path
) -> None:
    import subprocess

    repo = Path(repo).resolve()
    context = candidate(context)

    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(f"SOURCE_HEAD_UNAVAILABLE:{exc}") from exc

    producer_commit = context.get("producer_commit")
    producer_snapshot = context.get("producer_snapshot")

    if producer_commit is not None and producer_snapshot is not None:
        # Bind the image to its historical source tree independently from
        # the code that runs and validates the M4 controls.
        historical_snapshot = git_commit_snapshot(
            repo, context["source_commit"]
        )
        _contract_require(
            historical_snapshot == context["source_snapshot"],
            "PRODUCER_SOURCE_SNAPSHOT_MISMATCH",
        )

        try:
            ancestor = subprocess.run(
                [
                    "git", "merge-base", "--is-ancestor",
                    producer_commit, head,
                ],
                cwd=repo, capture_output=True,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise ValueError(f"PRODUCER_COMMIT_CHECK_FAILED:{exc}") from exc

        _contract_require(
            ancestor.returncode == 0,
            "PRODUCER_COMMIT_NOT_ANCESTOR_OF_HEAD",
        )
        _contract_require(
            producer_checkout_snapshot(repo) == producer_snapshot,
            "PRODUCER_CHECKOUT_SNAPSHOT_MISMATCH",
        )
        return

    # Legacy/non-candidate runs retain the original strict checkout binding.
    _contract_check_untracked_scope(repo)
    _contract_require(
        head == context["source_commit"], "PRODUCER_SOURCE_COMMIT_MISMATCH"
    )
    _contract_require(
        checkout_snapshot(repo) == context["source_snapshot"],
        "PRODUCER_SOURCE_SNAPSHOT_MISMATCH",
    )


def _contract_validate_dependency(
    report: Any,
    repo: Path,
    expected_verdict: str | None = None,
    policy_path: str | Path | None = None,
    expected_policy_sha256: str | None = None,
) -> None:
    """Bind dependency results to the source manifest and a pinned M4 policy."""
    import hashlib
    import re

    _contract_require(
        isinstance(report, dict), "DEPENDENCY_REPORT_NOT_OBJECT"
    )
    _contract_require(
        report.get("schema_version") == "1.0",
        "DEPENDENCY_REPORT_SCHEMA_INVALID",
    )
    _contract_require(
        report.get("scope") == "direct",
        "DEPENDENCY_REPORT_SCOPE_INVALID",
    )
    _contract_require(
        isinstance(report.get("reason"), str)
        and bool(report["reason"].strip()),
        "DEPENDENCY_REPORT_REASON_MISSING",
    )

    packages = report.get("packages")
    _contract_require(
        isinstance(packages, list) and bool(packages),
        "DEPENDENCY_REPORT_PACKAGES_EMPTY",
    )

    repo = Path(repo).resolve()
    actual_policy_path = Path(
        policy_path if policy_path is not None
        else repo / "cau-hinh/m4/dependency-policy.yml"
    ).resolve()
    _contract_require(
        actual_policy_path.is_file(), "M4_DEPENDENCY_POLICY_MISSING"
    )

    policy_bytes = actual_policy_path.read_bytes()
    actual_policy_sha256 = hashlib.sha256(policy_bytes).hexdigest()

    if expected_policy_sha256 is not None:
        _contract_require(
            _contract_hex(expected_policy_sha256, 64),
            "M4_POLICY_SHA256_INVALID",
        )
        _contract_require(
            actual_policy_sha256 == expected_policy_sha256,
            "M4_POLICY_SHA256_MISMATCH",
        )
        _contract_require(
            report.get("policy_sha256") == expected_policy_sha256,
            "DEPENDENCY_REPORT_POLICY_HASH_MISMATCH",
        )

    policy_text = policy_bytes.decode("utf-8").replace(chr(13), "")
    manifest_match = re.search(
        r"(?m)^[ \t]*path:[ \t]*(\S+)[ \t]*$", policy_text
    )
    _contract_require(
        manifest_match is not None, "M4_POLICY_MANIFEST_PATH_MISSING"
    )

    manifest = (repo / manifest_match.group(1)).resolve()
    _contract_require(
        manifest.is_relative_to(repo) and manifest.is_file(),
        "M4_DEPENDENCY_MANIFEST_MISSING_OR_OUT_OF_SCOPE",
    )
    expected_manifest_path = manifest.relative_to(repo).as_posix()
    _contract_require(
        report.get("manifest") == expected_manifest_path,
        "DEPENDENCY_REPORT_MANIFEST_PATH_MISMATCH",
    )

    manifest_sha256 = hashlib.sha256(manifest.read_bytes()).hexdigest()
    if report.get("manifest_sha256") is not None:
        _contract_require(
            report.get("manifest_sha256") == manifest_sha256,
            "DEPENDENCY_MANIFEST_SHA256_MISMATCH",
        )

    entries = re.findall(
        r"(?m)^[ \t]*-[ \t]*name:[ \t]*([^\s]+)[ \t]*\n"
        r"[ \t]*version:[ \t]*[\"']?([^\"'\s]+)[\"']?[ \t]*$",
        policy_text,
    )
    allowlist: dict[str, str] = {}
    for name, version in entries:
        _contract_require(
            name == name.lower() and name not in allowlist,
            "M4_POLICY_NAME_CASE_OR_DUPLICATE",
        )
        allowlist[name] = version
    _contract_require(bool(allowlist), "M4_POLICY_ALLOWLIST_EMPTY")

    expected_packages = []
    seen = set()
    for number, raw in enumerate(
        manifest.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s#]+)", line)
        _contract_require(
            match is not None,
            f"DEPENDENCY_REQUIREMENT_NOT_EXACT:{number}",
        )
        name, version = match.group(1).lower(), match.group(2)
        _contract_require(
            name not in seen, f"DEPENDENCY_DUPLICATE:{name}"
        )
        seen.add(name)
        expected_packages.append((name, version))

    _contract_require(bool(expected_packages), "DEPENDENCY_MANIFEST_EMPTY")

    reported_packages = []
    for package in packages:
        _contract_require(
            isinstance(package, dict)
            and isinstance(package.get("name"), str)
            and bool(package["name"].strip())
            and isinstance(package.get("version"), str)
            and type(package.get("approved")) is bool,
            "DEPENDENCY_REPORT_PACKAGE_INVALID",
        )
        name, version = package["name"], package["version"]
        _contract_require(
            name == name.lower(),
            "DEPENDENCY_REPORT_PACKAGE_NAME_NOT_NORMALIZED",
        )
        _contract_require(
            package["approved"] is (allowlist.get(name) == version),
            "DEPENDENCY_REPORT_APPROVAL_MISMATCH",
        )
        reported_packages.append((name, version))

    _contract_require(
        sorted(reported_packages) == sorted(expected_packages),
        "DEPENDENCY_REPORT_MANIFEST_MISMATCH",
    )

    actual_verdict = (
        "PASS"
        if all(allowlist.get(name) == version
               for name, version in expected_packages)
        else "FAIL"
    )
    _contract_require(
        report.get("status") == actual_verdict,
        "DEPENDENCY_REPORT_STATUS_MISMATCH",
    )
    if expected_verdict is not None:
        _contract_require(
            expected_verdict in {"PASS", "FAIL"}
            and actual_verdict == expected_verdict,
            "DEPENDENCY_VERDICT_CONTRADICTS_REPORT",
        )






def validate_vulnerability_report(
    report_path: str,
    artifact_subject: str | None,
    expected_artifact: str | None,
    expected_report_sha256: str | None = None,
) -> None:
    """Validate Trivy evidence; enforce immutable identity when supplied."""
    import re
    if not isinstance(expected_report_sha256, str) or not re.fullmatch(
        r"[0-9a-f]{64}", expected_report_sha256
    ):
        raise ValueError("VULNERABILITY_REPORT_SHA256_MISSING_OR_INVALID")
    try:
        actual_report_sha256 = sha256_file(report_path)
    except OSError as exc:
        raise ValueError(f"VULNERABILITY_REPORT_INVALID_JSON: {exc}") from exc
    if actual_report_sha256 != expected_report_sha256:
        raise ValueError("VULNERABILITY_REPORT_SHA256_MISMATCH")


    if not isinstance(artifact_subject, str) or not re.fullmatch(
        r"sha256:[0-9a-f]{64}", artifact_subject
    ):
        raise ValueError("VULNERABILITY_ARTIFACT_SUBJECT_INVALID")

    if not isinstance(expected_artifact, str) or not expected_artifact.strip():
        raise ValueError("VULNERABILITY_EXPECTED_ARTIFACT_MISSING")

    immutable = re.fullmatch(r".+@sha256:[0-9a-f]{64}", expected_artifact)
    if "@" in expected_artifact and not immutable:
        raise ValueError("VULNERABILITY_EXPECTED_ARTIFACT_INVALID")
    if immutable and expected_artifact.rsplit("@", 1)[1] != artifact_subject:
        raise ValueError("VULNERABILITY_EXPECTED_ARTIFACT_SUBJECT_MISMATCH")

    try:
        report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"VULNERABILITY_REPORT_INVALID_JSON: {exc}") from exc

    if not isinstance(report, dict):
        raise ValueError("VULNERABILITY_REPORT_NOT_OBJECT")

    schema = report.get("SchemaVersion")
    if type(schema) is not int or schema != 2:
        raise ValueError("VULNERABILITY_REPORT_SCHEMA_VERSION_INVALID")
    if report.get("ArtifactType") != "container_image":
        raise ValueError("VULNERABILITY_REPORT_ARTIFACT_TYPE_INVALID")
    if report.get("ArtifactName") != expected_artifact:
        raise ValueError("VULNERABILITY_REPORT_ARTIFACT_MISMATCH")

    metadata = report.get("Metadata")
    repo_digests = metadata.get("RepoDigests") if isinstance(metadata, dict) else None
    if not isinstance(repo_digests, list):
        raise ValueError("VULNERABILITY_REPORT_REPO_DIGESTS_MISSING")

    if immutable:
        digest_matches = expected_artifact in repo_digests
    else:
        repository = expected_artifact.rsplit(":", 1)[0]
        digest_matches = any(
            isinstance(item, str)
            and "@" in item
            and item.rsplit("@", 1)[0] == repository
            and item.rsplit("@", 1)[1] == artifact_subject
            for item in repo_digests
        )
    if not digest_matches:
        raise ValueError("VULNERABILITY_REPORT_DIGEST_MISMATCH")

    results = report.get("Results")
    if not isinstance(results, list) or not results:
        raise ValueError("VULNERABILITY_REPORT_RESULTS_INVALID")

    for index, result in enumerate(results):
        if not isinstance(result, dict):
            raise ValueError(f"VULNERABILITY_RESULT_{index}_INVALID")
        if not isinstance(result.get("Target"), str) or not result["Target"].strip():
            raise ValueError(f"VULNERABILITY_RESULT_{index}_TARGET_INVALID")

        vulnerabilities = result.get("Vulnerabilities")
        if vulnerabilities is not None and not isinstance(vulnerabilities, list):
            raise ValueError(f"VULNERABILITY_RESULT_{index}_VULNERABILITIES_INVALID")
        if isinstance(vulnerabilities, list):
            for item_index, item in enumerate(vulnerabilities):
                if not isinstance(item, dict):
                    raise ValueError(f"VULNERABILITY_RESULT_{index}_ITEM_{item_index}_INVALID")
                vuln_id = item.get("VulnerabilityID")
                if not isinstance(vuln_id, str) or not vuln_id.strip():
                    raise ValueError(f"VULNERABILITY_RESULT_{index}_ITEM_{item_index}_ID_INVALID")


def build_result(
    *,
    control_id: str,
    execution_status: str,
    policy_verdict: str,
    reason: str,
    run_id: str,
    source_snapshot: str,
    tool_name: str,
    tool_version: str,
    raw_exit_code: int | None,
    artifact_subject: str | None = None,
    report_path: str | None = None,
    expected_artifact: str | None = None,
    expected_report_sha256: str | None = None,
) -> dict[str, Any]:
    """Build and validate one normalized M4 result record."""

    control_id = control_id.strip().upper()
    execution_status = execution_status.strip().upper()
    policy_verdict = policy_verdict.strip().upper()

    if control_id not in VALID_CONTROLS:
        raise ValueError(f"Unsupported control_id: {control_id}")
    if execution_status not in VALID_EXECUTION_STATUSES:
        raise ValueError(f"Unsupported execution_status: {execution_status}")
    if policy_verdict not in VALID_VERDICTS:
        raise ValueError(f"Unsupported policy_verdict: {policy_verdict}")

    required_text = {
        "reason": reason,
        "run_id": run_id,
        "source_snapshot": source_snapshot,
        "tool_name": tool_name,
        "tool_version": tool_version,
    }
    for field, value in required_text.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string")

    if raw_exit_code is not None and (
        isinstance(raw_exit_code, bool) or not isinstance(raw_exit_code, int)
    ):
        raise ValueError("raw_exit_code must be an integer or null")

    if execution_status == "SUCCESS":
        if raw_exit_code not in (0, 1):
            raise ValueError("SUCCESS execution requires raw_exit_code 0 or 1")
        if policy_verdict == "PASS" and raw_exit_code != 0:
            raise ValueError("PASS verdict requires raw_exit_code 0")
        if policy_verdict == "FAIL" and raw_exit_code != 1:
            raise ValueError("FAIL verdict requires raw_exit_code 1")
        if policy_verdict not in ("PASS", "FAIL"):
            raise ValueError("SUCCESS execution requires PASS or FAIL verdict")

    if execution_status == "ERROR":
        if policy_verdict != "ERROR":
            raise ValueError("ERROR execution must have an ERROR verdict")
        if raw_exit_code not in (None, 2):
            raise ValueError("ERROR execution requires raw_exit_code 2 or null")

    if execution_status == "NOT_RUN":
        if policy_verdict != "NOT_RUN":
            raise ValueError("NOT_RUN execution must have a NOT_RUN verdict")
        if raw_exit_code is not None:
            raise ValueError("NOT_RUN execution requires raw_exit_code null")

    if policy_verdict == "PASS":
        if not isinstance(artifact_subject, str) or not artifact_subject.strip():
            raise ValueError("PASS verdict requires a non-empty artifact_subject")
        if not isinstance(report_path, str) or not report_path.strip():
            raise ValueError("PASS verdict requires a report_path")

    if control_id == "VULNERABILITY" and execution_status == "SUCCESS":
        if not isinstance(report_path, str) or not report_path.strip():
            raise ValueError(
                "Successful vulnerability evaluation requires report_path"
            )
        report_file = Path(report_path)
        if not report_file.is_file():
            raise ValueError(f"Report does not exist: {report_file}")
        validate_vulnerability_report(
            report_path,
            artifact_subject,
            expected_artifact,
            expected_report_sha256,
        )

    report_sha256 = None
    if report_path is not None:
        report = Path(report_path)
        if not report.is_file():
            raise ValueError(f"Report does not exist: {report}")
        report_sha256 = sha256_file(report)

    return {
        "schema_version": "1.0",
        "control_id": control_id,
        "execution_status": execution_status,
        "raw_exit_code": raw_exit_code,
        "policy_verdict": policy_verdict,
        "reason": reason.strip(),
        "source_snapshot": source_snapshot.strip(),
        "run_id": run_id.strip(),
        "artifact_subject": (
            artifact_subject.strip()
            if isinstance(artifact_subject, str)
            else artifact_subject
        ),
        "tool": {
            "name": tool_name.strip(),
            "version": tool_version.strip(),
        },
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "report": {
            "path": report_path,
            "sha256": report_sha256,
        },
    }


def write_fallback_error(args, error: Exception) -> bool:
    """Try to persist ERROR even when the requested result is invalid."""
    output = Path(args.output)
    control = args.control if args.control in VALID_CONTROLS else "UNKNOWN"
    report_path = None
    report_sha256 = None

    if args.report:
        candidate = Path(args.report)
        if candidate.is_file():
            try:
                report_path = str(candidate)
                report_sha256 = sha256_file(candidate)
            except OSError:
                report_path = None
                report_sha256 = None

    record = {
        "schema_version": "1.0",
        "control_id": control,
        "execution_status": "ERROR",
        "raw_exit_code": 2,
        "policy_verdict": "ERROR",
        "reason": f"ADAPTER_VALIDATION_ERROR: {error}"[:1000],
        "source_snapshot": args.source_snapshot or "UNAVAILABLE",
        "run_id": args.run_id or "UNAVAILABLE",
        "artifact_subject": args.artifact_subject or None,
        "tool": {
            "name": args.tool_name or "UNKNOWN",
            "version": args.tool_version or "UNAVAILABLE",
        },
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "report": {
            "path": report_path,
            "sha256": report_sha256,
        },
    }

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"RESULT_STATUS=ERROR")
        print(f"RESULT_PATH={output}")
        print(f"ADAPTER_ERROR={error}", file=sys.stderr)
        return True
    except OSError as exc:
        print(f"ADAPTER_ERROR={error}", file=sys.stderr)
        print(f"FALLBACK_WRITE_ERROR={exc}", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize one M4 control result into JSON."
    )
    parser.add_argument("--control", required=True, choices=sorted(VALID_CONTROLS))
    parser.add_argument(
        "--execution-status",
        required=True,
        choices=sorted(VALID_EXECUTION_STATUSES),
    )
    parser.add_argument("--verdict", required=True, choices=sorted(VALID_VERDICTS))
    parser.add_argument("--reason", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--source-snapshot", required=True)
    parser.add_argument("--tool-name", required=True)
    parser.add_argument("--tool-version", required=True)
    parser.add_argument("--exit-code", type=int, default=None)
    parser.add_argument("--artifact-subject")
    parser.add_argument("--expected-artifact")
    parser.add_argument("--expected-report-sha256")
    parser.add_argument("--report")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        result = build_result(
            control_id=args.control,
            execution_status=args.execution_status,
            policy_verdict=args.verdict,
            reason=args.reason,
            run_id=args.run_id,
            source_snapshot=args.source_snapshot,
            tool_name=args.tool_name,
            tool_version=args.tool_version,
            raw_exit_code=args.exit_code,
            artifact_subject=args.artifact_subject,
            report_path=args.report,
            expected_artifact=args.expected_artifact,
            expected_report_sha256=args.expected_report_sha256,
        )

        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"RESULT_STATUS={result['policy_verdict']}")
        print(f"RESULT_PATH={output}")
        return 0

    except (ValueError, OSError) as exc:
        write_fallback_error(args, exc)
        return 2





# ==============================================================================
# PR #12 INTEGRATION & RELEASE GATE EXTENSIONS (QUANG)
# ==============================================================================
CONTROLS = ('GITLEAKS','DEPENDENCY','UNIT_TEST','SBOM','DIGEST','COSIGN','VULNERABILITY','REGISTRY')
sha = sha256_file
require = _contract_require
hexid = _contract_hex
digest = _contract_digest

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def child(root, relative):
    require(isinstance(relative, str) and relative, 'missing relative path')
    p = (Path(root) / relative).resolve()
    require(p.is_relative_to(Path(root).resolve()), 'evidence path escape')
    require(p.is_file(), 'missing evidence: ' + relative)
    return p

def verify_archive(root, c):
    p = child(root, c.get('archive_path'))
    require(sha(p) == c['archive_sha256'], 'archive SHA mismatch')
    with tarfile.open(p, 'r:*') as t:
        if 'index.json' in t.getnames():
            def blob(d):
                f=t.extractfile('blobs/sha256/'+d.removeprefix('sha256:'));require(f is not None,'missing OCI blob');data=f.read();require('sha256:'+hashlib.sha256(data).hexdigest()==d,'OCI blob hash mismatch');return data
            layout=json.load(t.extractfile('index.json'));require(any(x.get('digest')==c['manifest_digest'] for x in layout.get('manifests',[])),'OCI layout/index mismatch')
            index=json.loads(blob(c['manifest_digest']));require(any(x.get('digest')==c['platform_manifest_digest'] for x in index.get('manifests',[])),'OCI platform identity')
            manifest=json.loads(blob(c['platform_manifest_digest']));require(manifest.get('config',{}).get('digest')==c['config_digest'],'OCI config identity')
            config=json.loads(blob(c['config_digest']));labels=config.get('config',{}).get('Labels',{})
            require(labels.get('org.opencontainers.image.revision')==c['source_commit'] and labels.get('orderflow.source_snapshot')==c['source_snapshot'],'build source labels mismatch')
            require(bool(manifest.get('layers')),'OCI layers missing')
            for layer in manifest['layers']:blob(layer['digest'])
            return p
        f = t.extractfile('manifest.json')
        require(f is not None, 'Docker archive manifest')
        m = json.load(f)
        require(isinstance(m, list) and len(m) == 1, 'single image archive required')
        f = t.extractfile(m[0]['Config'])
        require(f is not None, 'archive config missing')
        b = f.read()
        require('sha256:' + hashlib.sha256(b).hexdigest() == c['config_digest'], 'archive config digest mismatch')
        config = json.loads(b)
        labels = config.get('config', {}).get('Labels', {})
        require(labels.get('org.opencontainers.image.revision') == c['source_commit'] and labels.get('orderflow.source_snapshot') == c['source_snapshot'], 'build source labels mismatch')
        layers = m[0].get('Layers')
        diffids = config.get('rootfs', {}).get('diff_ids')
        require(isinstance(layers, list) and bool(layers) and isinstance(diffids, list) and len(layers) == len(diffids), 'archive layers')
        for path, expected in zip(layers, diffids):
            f = t.extractfile(path)
            require(f is not None, 'missing archive layer')
            h = hashlib.sha256()
            for chunk in iter(lambda: f.read(1024 * 1024), b''): h.update(chunk)
            require('sha256:' + h.hexdigest() == expected, 'archive layer tampering')
    return p

def verify_registry(root, c):
    p = child(root, c.get('registry_manifest_path'))
    require('sha256:' + sha(p) == c['platform_manifest_digest'], 'registry manifest digest mismatch')
    if c['manifest_digest']!=c['platform_manifest_digest']:
        index_path=child(root,c.get('registry_index_path','registry-index.json'));require('sha256:'+sha(index_path)==c['manifest_digest'],'registry index digest mismatch')
        require(any(x.get('digest')==c['platform_manifest_digest'] for x in read(index_path).get('manifests',[])),'index/platform mismatch')
    r = read(p)
    require(type(r.get('schemaVersion')) is int and r['schemaVersion'] == 2 and r.get('mediaType') in ('application/vnd.oci.image.manifest.v1+json', 'application/vnd.docker.distribution.manifest.v2+json'), 'registry schema')
    require(isinstance(r.get('config'), dict) and r['config'].get('digest') == c['config_digest'], 'registry config mismatch')
    require(isinstance(r.get('layers'), list) and bool(r['layers']) and all(isinstance(x, dict) and digest(x.get('digest')) for x in r['layers']), 'registry layers')
    return True

def bind_result(record, execution, context, source_root, target_root):
    c = candidate(context)
    r = json.loads(json.dumps(record))
    e = json.loads(json.dumps(execution))
    for value in (r, e):
        for key in ('source_commit', 'source_snapshot', 'run_id'):
            require(value.get(key) == c[key], 'handoff ' + key + ' mismatch')
        require(value.get('artifact_subject') == c['manifest_digest'], 'handoff subject mismatch')
    report = r.get('report', {})
    p = child(source_root, report.get('path'))
    require(sha(p) == report.get('sha256') == e.get('report_sha256'), 'handoff report hash mismatch')
    require(type(e.get('raw_exit_code')) is int and e['raw_exit_code'] == 0, 'handoff scanner execution failure')
    root = Path(target_root)
    root.mkdir(parents=True, exist_ok=True)
    name = r['control_id'].lower().replace('_', '-')
    output = root / (name + '-report.json')
    rp = root / (name + '-result.json')
    ep = root / (name + '-execution.json')
    require(not any(p.exists() for p in (output, rp, ep)), 'handoff refuses overwrite/stale evidence')
    shutil.copyfile(p, output)
    r['report']['path'] = output.name
    r['execution_path'] = ep.name
    ep.write_text(json.dumps(e, indent=2) + "\n", encoding='utf-8')
    rp.write_text(json.dumps(r, indent=2) + "\n", encoding='utf-8')
    validate_control(root, r['control_id'], c)
    return rp

def runtime_allowed():
    import ctypes, os, shutil
    if os.name == 'nt':
        class Memory(ctypes.Structure):
            _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [(n, ctypes.c_ulonglong) for n in ('total', 'available', 'page_total', 'page_available', 'virtual_total', 'virtual_available', 'extended')]
        m = Memory()
        m.length = ctypes.sizeof(m)
        require(ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)), 'cannot measure RAM')
        available = m.available
    else:
        values = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
        available = int(values['MemAvailable'].split()[0]) * 1024
    return available >= 1536 * 1048576 and shutil.disk_usage(Path(__file__).resolve().parents[1]).free >= 5 * 1073741824

def unit_main():
    import subprocess, xml.etree.ElementTree as ET, importlib.metadata, argparse
    p = argparse.ArgumentParser()
    p.add_argument('--unit', action='store_true')
    p.add_argument('--candidate', required=True)
    p.add_argument('--run-dir', required=True)
    a = p.parse_args()
    c = load_context(a.candidate)
    root = Path(a.run_dir).resolve()
    require(root.name == c['run_id'], 'unit run mismatch')
    report = root / 'unit-report.json'
    xml = root / 'unit.junit.xml'
    require(not report.exists() and not xml.exists(), 'unit producer refuses replay')
    cmd = [sys.executable, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', 'tests', '--basetemp', str(root / 'unit-temp'), '--junitxml', str(xml)]
    result = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=300)
    (root / 'unit-stdout.log').write_text(result.stdout, encoding='utf-8')
    (root / 'unit-stderr.log').write_text(result.stderr, encoding='utf-8')
    passed = failed = skipped = 0
    if xml.is_file():
        for t in ET.parse(xml).findall('.//testcase'):
            if t.find('failure') is not None or t.find('error') is not None: failed += 1
            elif t.find('skipped') is not None: skipped += 1
            else: passed += 1
    report.write_text(json.dumps({'passed': passed, 'failed': failed, 'skipped': skipped, 'layer': 'UNIT_CONTRACT', 'junit_sha256': sha(xml) if xml.is_file() else None}), encoding='utf-8')
    good = result.returncode == 0 and passed > 0 and failed == 0
    tool = {'name':'pytest','version':importlib.metadata.version('pytest')}
    emit_control(c,root,'UNIT_TEST',report,result.returncode,'PASS' if good else ('FAIL' if result.returncode==1 else 'ERROR'),tool,cmd,'Actual pytest/JUnit execution')
    print(result.stdout)
    print(result.stderr, file=sys.stderr)
    return 0 if good else 1



# PROPOSED_REFERENCE_CHANGE: m4-contract-1.0, canonical producer/consumer API.
from dataclasses import dataclass
CONTRACT_VERSION = 'm4-contract-1.0'
SOURCE_CONTROLS = {'GITLEAKS','DEPENDENCY','UNIT_TEST'}
NORMALIZED_CONTROLS = SOURCE_CONTROLS | {'SBOM','VULNERABILITY'}
_artifact_candidate = candidate

def candidate(value):
    if isinstance(value,dict) and value.get('evidence_kind')=='SOURCE_EXECUTION':
        require(value.get('contract')=='reference-1','candidate contract')
        require(hexid(value.get('source_commit'),40) and hexid(value.get('source_snapshot'),64),'source identity')
        require(isinstance(value.get('run_id'),str) and re.fullmatch(r'[A-Za-z0-9_-]{1,100}',value['run_id']),'run id')
        require(all(value.get(k) is None for k in ('artifact_subject','manifest_digest','config_digest','archive_sha256')),'source context must not fabricate artifact identity')
        return value
    return _artifact_candidate(value)

@dataclass(frozen=True)
class ControlAssessment:
    evidence_valid: bool
    security_approved: bool
    policy_verdict: str
    reason: str
    def __bool__(self):
        raise TypeError('Use evidence_valid or security_approved explicitly')

def _execution_subject(c,control):
    if control in SOURCE_CONTROLS:
        return {'kind':'source','source_commit':c['source_commit'],'source_snapshot':c['source_snapshot']}
    require(digest(c.get('manifest_digest')),'artifact subject required')
    return {'kind':'artifact','digest':c['manifest_digest']}

def _assess_envelope(r,e,c,root,repository_root=None,dependency_policy_path=None,expected_dependency_policy_sha256=None):
    c=candidate(c);require(isinstance(r,dict) and isinstance(e,dict),'record objects required')
    control=r.get('control_id');require(control in NORMALIZED_CONTROLS,'unsupported control')
    common={'source_commit','source_snapshot','run_id','contract_version','artifact_subject','execution_subject'}
    require(set(r)==common|{'schema_version','control_id','execution_status','raw_exit_code','policy_verdict','reason','tool','report','execution_path','wrapper_exit_code','policy_exit_code'},'result fields missing/unknown')
    require(set(e)==common|{'raw_exit_code','execution_started','report_sha256','tool','command','wrapper_exit_code','policy_exit_code'}|({'source_context'} if control=='GITLEAKS' else set()),'execution fields missing/unknown')
    require(isinstance(r.get('reason'),str) and bool(r['reason'].strip()),'reason required')
    require(r.get('schema_version')=='1.0' and r.get('contract_version')==CONTRACT_VERSION and e.get('contract_version')==CONTRACT_VERSION,'evidence contract version')
    for key in ('source_commit','source_snapshot','run_id'):
        require(r.get(key)==c[key] and e.get(key)==c[key],'record '+key+' mismatch')
    subject=_execution_subject(c,control);artifact=None if control in SOURCE_CONTROLS else c['manifest_digest']
    require(r.get('execution_subject')==subject and e.get('execution_subject')==subject,'execution subject mismatch')
    require(r.get('artifact_subject')==artifact and e.get('artifact_subject')==artifact,'artifact subject mismatch')
    verdict=r.get('policy_verdict');require(verdict in ('PASS','FAIL','ERROR'),'policy verdict enum')
    status='ERROR' if verdict=='ERROR' else 'SUCCESS';require(r.get('execution_status')==status,'execution status mismatch')
    code=r.get('raw_exit_code');require(type(code) is int or (code is None and verdict=='ERROR'),'raw exit must be integer or ERROR/null')
    require(type(e.get('raw_exit_code')) is type(code) and e.get('raw_exit_code')==code,'raw exit mismatch')
    require(type(e.get('execution_started')) is bool and e['execution_started']==(code is not None),'execution started mismatch')
    require(verdict!='PASS' or code==0,'NONZERO_RAW_EXIT_CANNOT_PASS')
    require(status!='SUCCESS' or (type(code) is int and code in (0,1)),'successful execution raw exit must be 0 or 1')
    tool=r.get('tool');require(isinstance(tool,dict) and all(isinstance(tool.get(k),str) and tool[k].strip() for k in ('name','version')) and e.get('tool')==tool,'tool identity missing/mismatch')
    command=e.get('command');require(isinstance(command,list) and bool(command) and all(isinstance(x,str) and x for x in command),'execution command required')
    if verdict=='PASS':require(not any(tool[k] in ('UNKNOWN','UNAVAILABLE') for k in ('name','version')),'PASS requires actual tool identity')
    stem=control.lower().replace('_','-');require(r.get('execution_path')==stem+'-execution.json','execution path mismatch')
    for key in ('wrapper_exit_code','policy_exit_code'):
        v=r.get(key);require(v is None or type(v) is int,'typed '+key);require(v==e.get(key),key+' mismatch')
    if control=='GITLEAKS':
        sc=e.get('source_context');require(isinstance(sc,dict) and all(k in sc for k in ('scope','head_commit','dirty','shallow','raw_exit_codes','scanner_integrity')),'source context fields')
        require(sc.get('dirty') is None or type(sc['dirty']) is bool,'dirty boolean')
        require(sc.get('shallow') is None or type(sc['shallow']) is bool,'shallow boolean')
        if verdict=='PASS':
            require(sc['scope']=='FULL_HISTORY_AND_WORKTREE' and sc['head_commit']==c['source_commit'] and sc['dirty'] is False and sc['shallow'] is False,'source scope/context')
            require(sc['raw_exit_codes']==[0,0] and all(type(x) is int for x in sc['raw_exit_codes']),'both source scopes must execute')
    ref=r.get('report');payload=None
    if ref is None:
        require(verdict=='ERROR' and e.get('report_sha256') is None,'missing report cannot approve')
    else:
        require(isinstance(ref,dict) and hexid(ref.get('sha256'),64),'report identity')
        p=child(root,ref.get('path'));require(sha(p)==ref['sha256']==e.get('report_sha256'),'CONTROL_REPORT_HASH_MISMATCH')
        if verdict!='ERROR':
            try:payload=json.loads(p.read_text(encoding='utf-8'))
            except (ValueError,UnicodeError) as exc:raise ValueError('malformed report') from exc
    if verdict!='ERROR':
        require(payload is not None,'missing report')
        if control=='GITLEAKS':
            require(isinstance(payload,list),'Gitleaks report list');require((verdict=='PASS')==(not payload),'Gitleaks verdict/findings contradiction')
        elif control=='SBOM':validate_spdx(payload)
        elif control=='VULNERABILITY':require((verdict=='PASS')==validate_trivy(payload,c),'vulnerability verdict/report contradiction')
        elif control=='DEPENDENCY':
            repo=Path(repository_root or Path(__file__).resolve().parents[1]);policy=Path(dependency_policy_path or repo/'cau-hinh/m4/dependency-policy.yml')
            require(payload.get('policy_sha256')==sha(policy),'dependency policy hash mismatch')
            manifest=child(repo,payload.get('manifest'));require(payload.get('manifest_sha256')==sha(manifest),'dependency manifest hash mismatch')
            _contract_validate_dependency(payload,repo,expected_verdict=verdict,policy_path=dependency_policy_path,expected_policy_sha256=expected_dependency_policy_sha256)
        elif control=='UNIT_TEST':
            require(isinstance(payload,dict) and all(type(payload.get(k)) is int and payload[k]>=0 for k in ('passed','failed')) and payload.get('layer')=='UNIT_CONTRACT','unit report counts')
            require((verdict=='PASS')==(payload['passed']>0 and payload['failed']==0),'unit verdict/count contradiction')
    return ControlAssessment(True,verdict=='PASS' and status=='SUCCESS' and code==0,verdict,'VALID_RECORD_NOT_AUTOMATIC_APPROVAL')

def validate_control(run_dir,control,context,repository_root=None,dependency_policy_path=None,expected_dependency_policy_sha256=None):
    c=candidate(context);require(control in NORMALIZED_CONTROLS,'unsupported control')
    root=Path(run_dir).resolve();require(root.name==c['run_id'],'run directory identity')
    stem=control.lower().replace('_','-');r=read(child(root,stem+'-result.json'));e=read(child(root,stem+'-execution.json'))
    require(r.get('control_id')==control,'control identity mismatch')
    return _assess_envelope(r,e,c,root,repository_root,dependency_policy_path,expected_dependency_policy_sha256)

def emit_control(context,run_dir,control,report_path,raw_exit,verdict,tool,command,reason,*,wrapper_exit_code=None,policy_exit_code=None,repository_root=None,dependency_policy_path=None,expected_dependency_policy_sha256=None,scope=None,head_commit=None,dirty=None,shallow=None,raw_exit_codes=None,scanner_integrity=None):
    c=candidate(context);repo=Path(repository_root or Path(__file__).resolve().parents[1]).resolve();_contract_check_current_context(c,repo)
    root=Path(run_dir).resolve();require(root.name==c['run_id'] and not root.is_relative_to(repo),'run output must be separate and run-bound')
    require(control in NORMALIZED_CONTROLS,'unsupported control');require(isinstance(reason,str) and reason.strip(),'reason required')
    stem=control.lower().replace('_','-');rp=root/(stem+'-result.json');ep=root/(stem+'-execution.json');require(not rp.exists() and not ep.exists(),'producer refuses overwrite')
    report=None
    if report_path is not None:
        p=Path(report_path).resolve();require(p.is_relative_to(root) and p.is_file(),'report must exist inside run');report={'path':p.relative_to(root).as_posix(),'sha256':sha(p)}
    common={k:c[k] for k in ('source_commit','source_snapshot','run_id')};common.update(contract_version=CONTRACT_VERSION,artifact_subject=None if control in SOURCE_CONTROLS else c.get('manifest_digest'),execution_subject=_execution_subject(c,control))
    e={**common,'raw_exit_code':raw_exit,'execution_started':raw_exit is not None,'report_sha256':report['sha256'] if report else None,'tool':tool,'command':command,'wrapper_exit_code':wrapper_exit_code,'policy_exit_code':policy_exit_code}
    if control=='GITLEAKS':e['source_context']={'scope':scope,'head_commit':head_commit,'dirty':dirty,'shallow':shallow,'raw_exit_codes':raw_exit_codes,'scanner_integrity':scanner_integrity}
    r={**common,'schema_version':'1.0','control_id':control,'execution_status':'ERROR' if verdict=='ERROR' else 'SUCCESS','raw_exit_code':raw_exit,'policy_verdict':verdict,'reason':reason,'tool':tool,'report':report,'execution_path':ep.name,'wrapper_exit_code':wrapper_exit_code,'policy_exit_code':policy_exit_code}
    _assess_envelope(r,e,c,root,repo,dependency_policy_path,expected_dependency_policy_sha256)
    root.mkdir(parents=True,exist_ok=True)
    for path,data in ((ep,e),(rp,r)):
        pending=path.with_suffix(path.suffix+'.pending');require(not pending.exists(),'unfinished publication exists');pending.write_bytes((json.dumps(data,indent=2)+'\n').encode());pending.replace(path)
    return rp

if __name__ == '__main__':
    raise SystemExit(unit_main() if '--unit' in sys.argv else main())
