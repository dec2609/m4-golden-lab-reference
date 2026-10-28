#!/usr/bin/env python3
"""Run M4 SBOM and vulnerability controls against a Docker image."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SBOM_SCRIPT = ROOT / "scripts/generate_sbom_m4.py"
VULN_SCRIPT = ROOT / "scripts/vulnerability_scan.py"
ADAPTER = ROOT / "scripts/m4_result_adapter.py"

DEFAULT_IMAGE = "localhost:5000/order-app:v1.0.0"
DEFAULT_POLICY = ROOT / "cau-hinh/m4/vulnerability-policy.json"
DEFAULT_OUTPUT = ROOT / "bang-chung/m4/results"

SBOM_REPORT = ROOT / "bang-chung/m4/sbom/order-app.spdx.json"
SBOM_EVIDENCE = ROOT / "bang-chung/m4/sbom/sbom-evidence.txt"
TRIVY_REPORT = ROOT / "bang-chung/m4/vulnerability/trivy-report.json"
POLICY_REPORT = (
    ROOT / "bang-chung/m4/vulnerability/vulnerability-policy-result.json"
)


def run(command):
    """Run a command without raising when the process exits unsuccessfully."""
    try:
        return subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        failed = subprocess.CompletedProcess(command, 127, "", str(exc))
        failed.execution_started = False
        return failed


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def get_status(output, key):
    prefix = key + "="
    for line in output.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return None


def get_value(output, key):
    return get_status(output, key)


def run_trivy_if_fresh(command, freshness_exec, freshness_status, result_path):
    """Run Trivy only when freshness execution and its persisted result both pass."""
    valid = (
        freshness_exec.returncode == 0
        and freshness_status == "PASS"
        and Path(result_path).is_file()
    )

    if valid:
        try:
            result = json.loads(Path(result_path).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            valid = False
        else:
            valid = isinstance(result, dict) and result.get("status") == "PASS"

    if not valid:
        blocked = subprocess.CompletedProcess(
            command,
            2,
            "",
            "TRIVY_DATABASE_FRESHNESS_CHECK_FAILED",
        )
        blocked.execution_started = False
        return blocked

    return run(command)


def get_source_snapshot():
    """Fingerprint the relevant source files, including uncommitted changes."""
    paths = [
        Path(__file__).resolve(),
        SBOM_SCRIPT,
        VULN_SCRIPT,
        ADAPTER,
        DEFAULT_POLICY,
    ]
    digest = hashlib.sha256()

    for path in paths:
        digest.update(str(path.relative_to(ROOT)).encode("utf-8"))
        digest.update(b"\0")
        if path.is_file():
            digest.update(path.read_bytes())
        else:
            digest.update(b"MISSING")
        digest.update(b"\0")

    return "sha256:" + digest.hexdigest()


def get_tool_version(command):
    result = run(command)
    output = (result.stdout + "\n" + result.stderr).strip()
    if result.returncode != 0 or not output:
        return "UNAVAILABLE"
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    for line in lines:
        if line.lower().startswith("version:"):
            version = line.split(":", 1)[1].strip()
            return version or "UNAVAILABLE"
    return "UNAVAILABLE"



def inspect_image(image):
    """Resolve either an exact tag or an exact immutable repository digest."""
    result = run(["docker", "image", "inspect", image])

    if result.returncode != 0:
        raise RuntimeError(
            "DOCKER_IMAGE_INSPECT_FAILED: "
            + (result.stderr.strip() or result.stdout.strip() or "no details")
        )

    try:
        objects = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("DOCKER_INSPECT_JSON_INVALID") from exc

    if not isinstance(objects, list) or not objects:
        raise RuntimeError("DOCKER_IMAGE_NOT_FOUND")

    item = objects[0]
    if not isinstance(item, dict):
        raise RuntimeError("DOCKER_IMAGE_METADATA_INVALID")

    tags = item.get("RepoTags") or []
    repo_digests = item.get("RepoDigests") or []
    image_id = item.get("Id")

    if "@" in image:
        repository, digest_part = image.rsplit("@", 1)
        if (
            not repository
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest_part)
        ):
            raise RuntimeError("DOCKER_IMMUTABLE_REFERENCE_INVALID")

        matching = [
            entry for entry in repo_digests
            if isinstance(entry, str) and entry == image
        ]
        if not matching:
            raise RuntimeError("DOCKER_IMMUTABLE_REPO_DIGEST_MISMATCH")
        artifact_subject = digest_part
        repository_digest = image
    else:
        if image not in tags:
            raise RuntimeError("DOCKER_IMAGE_TAG_MISMATCH")

        repository = image.rsplit(":", 1)[0]
        matching = [
            entry for entry in repo_digests
            if isinstance(entry, str)
            and entry.startswith(repository + "@sha256:")
        ]
        if not matching:
            raise RuntimeError("DOCKER_REPOSITORY_DIGEST_MISSING")

        repository_digest = matching[0]
        digest_part = repository_digest.rsplit("@", 1)[-1]
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest_part):
            raise RuntimeError("DOCKER_REPOSITORY_DIGEST_INVALID")
        artifact_subject = digest_part

    return {
        "image": image,
        "image_id": image_id,
        "repo_tags": tags,
        "repo_digests": repo_digests,
        "artifact_subject": artifact_subject,
        "repository_digest": repository_digest,
    }


def normalize(
    *,
    control,
    execution_status,
    verdict,
    reason,
    run_id,
    snapshot,
    tool_name,
    tool_version,
    output_path,
    exit_code=None,
    artifact_subject=None,
    report_path=None,
    expected_artifact=None,
    expected_report_sha256=None,
):
    command = [
        sys.executable,
        str(ADAPTER),
        "--control", control,
        "--execution-status", execution_status,
        "--verdict", verdict,
        "--reason", reason[:1000],
        "--run-id", run_id,
        "--source-snapshot", snapshot,
        "--tool-name", tool_name,
        "--tool-version", tool_version,
        "--output", str(output_path),
    ]

    if exit_code is not None:
        command.extend(["--exit-code", str(exit_code)])
    if artifact_subject:
        command.extend(["--artifact-subject", artifact_subject])
    if expected_artifact:
        command.extend(["--expected-artifact", expected_artifact])
    if expected_report_sha256:
        command.extend([
            "--expected-report-sha256", expected_report_sha256
        ])
    if report_path is not None and Path(report_path).is_file():
        command.extend(["--report", str(report_path)])

    result = run(command)

    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)

    return result.returncode == 0


def record_error_for_both(
    *,
    run_id,
    snapshot,
    run_dir,
    reason,
    syft_version,
    trivy_version,
):
    """Record fail-closed outcomes when image identity cannot be verified."""
    for control, tool, version, output_name in (
        ("SBOM", "syft", syft_version, "sbom-result.json"),
        (
            "VULNERABILITY",
            "trivy",
            trivy_version,
            "vulnerability-result.json",
        ),
    ):
        normalize(
            control=control,
            execution_status="ERROR",
            verdict="ERROR",
            reason=reason,
            run_id=run_id,
            snapshot=snapshot,
            tool_name=tool,
            tool_version=version,
            output_path=run_dir / output_name,
            exit_code=2,
        )


def main():
    parser = argparse.ArgumentParser(
        description="Run M4 SBOM and vulnerability controls on a Docker image."
    )
    parser.add_argument("--image")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--output-dir")
    parser.add_argument("--run-dir", help="Canonical same-run directory; alias for output parent plus candidate run_id")
    parser.add_argument("--run-id")
    parser.add_argument(
        "--candidate", type=Path,
        help="Run all M4 controls against a validated immutable candidate",
    )
    args = parser.parse_args()
    if args.run_dir:
        if not args.candidate: parser.error('--run-dir requires --candidate')
        from m4_result_adapter import read
        target=Path(args.run_dir).resolve()
        if target.name != read(args.candidate)['run_id']: parser.error('run directory/candidate mismatch')
        args.output_dir=str(target.parent)

    if args.candidate is not None:
        try:
            from scripts.m4_candidate_controls import run_candidate_controls
            return run_candidate_controls(args)
        except Exception as exc:
            print("CANDIDATE_STATUS=ERROR", file=sys.stderr)
            print(f"REASON={exc}", file=sys.stderr)
            return 2

    image = (args.image or DEFAULT_IMAGE).strip()
    if not image:
        parser.error("--image must not be empty")

    policy = Path(args.policy).resolve()
    output_root = Path(args.output_dir or DEFAULT_OUTPUT).resolve()

    if not policy.is_file():
        parser.error(f"Policy file does not exist: {policy}")

    run_id = args.run_id or (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid4().hex[:8]
    )
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", run_id):
        parser.error("Invalid --run-id")

    run_dir = output_root / run_id
    if run_dir.exists() and any(run_dir.iterdir()):
        parser.error(f"Output directory is not empty: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)

    # Each run owns its SBOM, Trivy and policy reports.
    sbom_output_dir = run_dir / "sbom"
    sbom_report = sbom_output_dir / "order-app.spdx.json"
    trivy_report = run_dir / "trivy-report.json"
    policy_report = run_dir / "vulnerability-policy-result.json"

    snapshot = get_source_snapshot()
    syft_version = get_tool_version(["syft", "version"])
    trivy_version = get_tool_version(["trivy", "--version"])

    print(f"RUN_ID={run_id}")
    print(f"SOURCE_SNAPSHOT={snapshot}")
    print(f"IMAGE={image}")
    print(f"OUTPUT_DIR={run_dir}")

    # Step 1: Resolve image identity before scanning.
    try:
        identity = inspect_image(image)
        artifact_subject = identity["artifact_subject"]
    except RuntimeError as exc:
        reason = str(exc)
        write_json(run_dir / "image-identity-evidence.json", {
            "image": image,
            "status": "ERROR",
            "reason": reason,
        })
        record_error_for_both(
            run_id=run_id,
            snapshot=snapshot,
            run_dir=run_dir,
            reason=reason,
            syft_version=syft_version,
            trivy_version=trivy_version,
        )
        print(f"IMAGE_IDENTITY_STATUS=ERROR")
        print(f"REASON={reason}")
        return 2

    write_json(run_dir / "image-identity-evidence.json", {
        **identity,
        "status": "PASS",
        "source_snapshot": snapshot,
        "run_id": run_id,
    })

    print(f"IMAGE_ID={identity.get('image_id') or 'UNAVAILABLE'}")
    print(f"ARTIFACT_SUBJECT={artifact_subject}")
    print(f"REPOSITORY_DIGEST={identity['repository_digest']}")

    # Step 2: Generate SPDX SBOM using the configured direct-image generator.
    # Remove stale reports first so an old file can never count as fresh output.
    for path in (sbom_report, trivy_report, policy_report):
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            reason = f"STALE_REPORT_CLEANUP_FAILED: {path}: {exc}"
            write_json(run_dir / "report-cleanup-error.json", {
                "status": "ERROR",
                "reason": reason,
            })
            record_error_for_both(
                run_id=run_id,
                snapshot=snapshot,
                run_dir=run_dir,
                reason=reason,
                syft_version=syft_version,
                trivy_version=trivy_version,
            )
            return 2

    sbom_command = [
        sys.executable, str(SBOM_SCRIPT),
        "--image", image,
        "--output-dir", str(sbom_output_dir),
    ]
    sbom_exec = run(sbom_command)

    if sbom_exec.stdout.strip():
        print(sbom_exec.stdout.strip())
    if sbom_exec.stderr.strip():
        print(sbom_exec.stderr.strip(), file=sys.stderr)

    sbom_status = get_status(sbom_exec.stdout, "SBOM_STATUS")
    sbom_subject = get_value(sbom_exec.stdout, "ARTIFACT_SUBJECT")
    sbom_report_exists = sbom_report.is_file()

    sbom_identity_matches = (
        sbom_subject is not None and sbom_subject == artifact_subject
    )

    write_json(run_dir / "sbom-execution-evidence.json", {
        "run_id": run_id,
        "source_snapshot": snapshot,
        "image": image,
        "artifact_subject": artifact_subject,
        "sbom_artifact_subject": sbom_subject,
        "artifact_identity_matches": sbom_identity_matches,
        "command": sbom_command,
        "raw_exit_code": sbom_exec.returncode,
        "status": sbom_status or "ERROR",
        "stdout": sbom_exec.stdout,
        "stderr": sbom_exec.stderr,
        "tool": "syft",
        "tool_version": syft_version,
        "report_path": str(sbom_report),
        "report_exists": sbom_report_exists,
    })

    if (
        sbom_exec.returncode == 0
        and sbom_status == "PASS"
        and sbom_report_exists
        and sbom_identity_matches
    ):
        sbom_verdict = "PASS"
        sbom_execution = "SUCCESS"
        sbom_exit_code = 0
        sbom_reason = "SBOM generated and image identity verified."
    elif sbom_exec.returncode == 1 and sbom_status == "FAIL":
        sbom_verdict = "FAIL"
        sbom_execution = "SUCCESS"
        sbom_exit_code = 1
        sbom_reason = "SBOM control reported validation failure."
    else:
        sbom_verdict = "ERROR"
        sbom_execution = "ERROR"
        sbom_exit_code = 2
        sbom_reason = (
            "SBOM execution, report, status, or artifact identity validation "
            "failed."
        )

    sbom_adapter_ok = normalize(
        control="SBOM",
        execution_status=sbom_execution,
        verdict=sbom_verdict,
        reason=sbom_reason,
        run_id=run_id,
        snapshot=snapshot,
        tool_name="syft",
        tool_version=syft_version,
        output_path=run_dir / "sbom-result.json",
        exit_code=sbom_exit_code,
        artifact_subject=artifact_subject,
        report_path=sbom_report if sbom_report_exists else None,
    )

    # Step 3: Check Trivy DB freshness and scan the immutable repository digest.
    repository_digest = identity["repository_digest"]
    metadata_path = Path.home() / ".cache/trivy/db/metadata.json"
    freshness_result_path = run_dir / "trivy-reproducibility-result.json"
    freshness_command = [
        sys.executable, str(ROOT / "scripts/trivy_reproducibility.py"),
        "--version", trivy_version,
        "--metadata", str(metadata_path),
        "--max-age-hours", "24",
        "--output", str(freshness_result_path),
    ]
    freshness_exec = run(freshness_command)
    if freshness_exec.stdout.strip():
        print(freshness_exec.stdout.strip())
    if freshness_exec.stderr.strip():
        print(freshness_exec.stderr.strip(), file=sys.stderr)
    freshness_status = get_status(
        freshness_exec.stdout, "REPRODUCIBILITY_STATUS"
    )
    freshness_reason = get_status(freshness_exec.stdout, "REASON") or (
        "Freshness checker returned no reason."
    )
    write_json(run_dir / "trivy-reproducibility-execution-evidence.json", {
        "run_id": run_id,
        "source_snapshot": snapshot,
        "command": freshness_command,
        "raw_exit_code": freshness_exec.returncode,
        "status": freshness_status or "ERROR",
        "reason": freshness_reason,
        "stdout": freshness_exec.stdout,
        "stderr": freshness_exec.stderr,
        "trivy_version": trivy_version,
        "metadata_path": str(metadata_path),
        "metadata_exists": metadata_path.is_file(),
        "result_path": str(freshness_result_path),
        "result_exists": freshness_result_path.is_file(),
    })
    trivy_command = [
        "trivy", "image",
        "--format", "json",
        "--output", str(trivy_report),
        repository_digest,
    ]
    trivy_exec = run_trivy_if_fresh(
        trivy_command,
        freshness_exec,
        freshness_status,
        freshness_result_path,
    )

    if trivy_exec.stdout.strip():
        print(trivy_exec.stdout.strip())
    if trivy_exec.stderr.strip():
        print(trivy_exec.stderr.strip(), file=sys.stderr)

    trivy_report_exists = trivy_report.is_file()
    trivy_report_sha256 = (
        hashlib.sha256(trivy_report.read_bytes()).hexdigest()
        if trivy_report_exists else None
    )

    write_json(run_dir / "trivy-execution-evidence.json", {
        "run_id": run_id,
        "source_snapshot": snapshot,
        "image": image,
        "artifact_subject": artifact_subject,
        "command": trivy_command,
        "raw_exit_code": trivy_exec.returncode,
        "status": "SUCCESS" if trivy_exec.returncode == 0 else "ERROR",
        "stdout": trivy_exec.stdout,
        "stderr": trivy_exec.stderr,
        "tool": "trivy",
        "tool_version": trivy_version,
        "report_path": str(trivy_report),
        "report_exists": trivy_report_exists,
        "report_sha256": trivy_report_sha256,
    })

    if trivy_exec.returncode != 0 or not trivy_report_exists:
        vuln_verdict = "ERROR"
        vuln_execution = "ERROR"
        vuln_exit_code = 2
        vuln_reason = (
            f"Trivy failed or its report is missing; "
            f"raw_exit_code={trivy_exec.returncode}."
        )
        policy_status = "ERROR"
        policy_exec = None
    else:
        # Step 4: Require exact ArtifactName match before policy evaluation.
        policy_command = [
            sys.executable, str(VULN_SCRIPT),
            "--report", str(trivy_report),
            "--policy", str(policy),
            "--expected-artifact", repository_digest,
            "--expected-digest", artifact_subject,
            "--expected-report-sha256", trivy_report_sha256,
            "--output", str(policy_report),
        ]
        policy_exec = run(policy_command)

        if policy_exec.stdout.strip():
            print(policy_exec.stdout.strip())
        if policy_exec.stderr.strip():
            print(policy_exec.stderr.strip(), file=sys.stderr)

        policy_status = get_status(
            policy_exec.stdout, "VULNERABILITY_STATUS"
        )
        policy_reason = get_status(policy_exec.stdout, "REASON") or (
            "Policy evaluator returned no reason."
        )

        write_json(run_dir / "vulnerability-policy-execution-evidence.json", {
            "run_id": run_id,
            "source_snapshot": snapshot,
            "command": policy_command,
            "raw_exit_code": policy_exec.returncode,
            "status": policy_status or "ERROR",
            "stdout": policy_exec.stdout,
            "stderr": policy_exec.stderr,
            "policy_path": str(policy),
            "expected_artifact": repository_digest,
            "expected_digest": artifact_subject,
            "report_path": str(trivy_report),
        })

        if policy_exec.returncode == 0 and policy_status == "PASS":
            vuln_verdict = "PASS"
            vuln_execution = "SUCCESS"
            vuln_exit_code = 0
            vuln_reason = policy_reason
        elif policy_exec.returncode == 1 and policy_status == "FAIL":
            vuln_verdict = "FAIL"
            vuln_execution = "SUCCESS"
            vuln_exit_code = 1
            vuln_reason = policy_reason
        else:
            vuln_verdict = "ERROR"
            vuln_execution = "ERROR"
            vuln_exit_code = 2
            vuln_reason = (
                f"Policy evaluation failed: exit={policy_exec.returncode}; "
                f"status={policy_status!r}; {policy_reason}"
            )

    # Policy PASS cannot override a stale or unverifiable Trivy DB.
    if freshness_exec.returncode != 0 or freshness_status != "PASS":
        vuln_verdict = "ERROR"
        vuln_execution = "ERROR"
        vuln_exit_code = 2
        vuln_reason = (
            "TRIVY_DATABASE_FRESHNESS_CHECK_FAILED: "
            f"status={freshness_status!r}; {freshness_reason}"
        )

    vuln_adapter_ok = normalize(
        control="VULNERABILITY",
        execution_status=vuln_execution,
        verdict=vuln_verdict,
        reason=vuln_reason,
        run_id=run_id,
        snapshot=snapshot,
        tool_name="trivy",
        tool_version=trivy_version,
        output_path=run_dir / "vulnerability-result.json",
        exit_code=vuln_exit_code,
        artifact_subject=artifact_subject,
        report_path=trivy_report if trivy_report_exists else None,
        expected_artifact=repository_digest,
        expected_report_sha256=trivy_report_sha256,
    )

    print(f"SBOM_RESULT={run_dir / 'sbom-result.json'}")
    print(f"VULNERABILITY_RESULT={run_dir / 'vulnerability-result.json'}")
    print(f"SBOM_REPORT={sbom_report if sbom_report.is_file() else 'NOT_CREATED'}")
    print(f"TRIVY_REPORT={trivy_report if trivy_report.is_file() else 'NOT_CREATED'}")
    print(f"POLICY_REPORT={policy_report if policy_report.is_file() else 'NOT_CREATED'}")
    print(f"RUN_EVIDENCE_DIR={run_dir}")
    print(f"SBOM_VERDICT={sbom_verdict}")
    print(f"VULNERABILITY_VERDICT={vuln_verdict}")

    if not sbom_adapter_ok or not vuln_adapter_ok:
        return 2
    if "ERROR" in (sbom_verdict, vuln_verdict):
        return 2
    if "FAIL" in (sbom_verdict, vuln_verdict):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
