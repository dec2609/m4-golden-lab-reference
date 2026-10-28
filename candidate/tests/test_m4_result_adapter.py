
import hashlib
import json
from pathlib import Path

import pytest

from scripts.m4_result_adapter import build_result


def make_result(**overrides):
    data = {
        "control_id": "DEPENDENCY",
        "execution_status": "SUCCESS",
        "policy_verdict": "PASS",
        "reason": "POLICY_SATISFIED",
        "run_id": "test-run-001",
        "source_snapshot": "git:abc123",
        "tool_name": "dependency-policy",
        "tool_version": "1.0",
        "raw_exit_code": 0,
    }
    data.update(overrides)
    if (
        data.get("control_id") == "VULNERABILITY"
        and data.get("report_path")
        and "expected_report_sha256" not in overrides
    ):
        report = Path(data["report_path"])
        if report.is_file():
            data["expected_report_sha256"] = hashlib.sha256(
                report.read_bytes()
            ).hexdigest()
    return build_result(**data)


def make_report(tmp_path):
    """Create a minimal report file for adapter tests."""
    report = tmp_path / "report.json"
    report.write_text(
        json.dumps({"Results": [{"Target": "fixture-package-scan", "Vulnerabilities": []}]}),
        encoding="utf-8",
    )
    return report


def test_valid_pass_result_has_required_fields(tmp_path):
    report = make_report(tmp_path)

    result = make_result(
        artifact_subject="sha256:" + ("a" * 64),
        report_path=str(report),
    )

    assert result["control_id"] == "DEPENDENCY"
    assert result["execution_status"] == "SUCCESS"
    assert result["policy_verdict"] == "PASS"
    assert result["run_id"] == "test-run-001"
    assert result["schema_version"] == "1.0"
    assert result["timestamp_utc"].endswith("+00:00")
    assert result["raw_exit_code"] == 0
    assert result["artifact_subject"] == "sha256:" + ("a" * 64)
    assert result["report"]["path"] == str(report)
    assert len(result["report"]["sha256"]) == 64


@pytest.mark.parametrize(
    ("execution_status", "policy_verdict"),
    [
        ("ERROR", "PASS"),
        ("NOT_RUN", "PASS"),
        ("ERROR", "FAIL"),
        ("NOT_RUN", "FAIL"),
    ],
)
def test_unsafe_execution_cannot_be_pass_or_fail(
    execution_status,
    policy_verdict,
):
    with pytest.raises(ValueError):
        make_result(
            execution_status=execution_status,
            policy_verdict=policy_verdict,
        )


def test_error_requires_error_verdict():
    with pytest.raises(ValueError):
        make_result(
            execution_status="ERROR",
            policy_verdict="FAIL",
        )


def test_not_run_requires_not_run_verdict():
    with pytest.raises(ValueError):
        make_result(
            execution_status="NOT_RUN",
            policy_verdict="ERROR",
        )


def test_unknown_control_is_rejected():
    with pytest.raises(ValueError, match="Unsupported control_id"):
        make_result(control_id="UNKNOWN")


def test_empty_run_id_is_rejected():
    with pytest.raises(ValueError, match="run_id"):
        make_result(run_id=" ")


def test_report_hash_is_recorded(tmp_path):
    report = make_report(tmp_path)

    result = make_result(
        artifact_subject="sha256:" + ("a" * 64),
        report_path=str(report),
    )

    assert result["report"]["sha256"]
    assert len(result["report"]["sha256"]) == 64


def test_missing_report_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="Report does not exist"):
        make_result(
            artifact_subject="sha256:" + ("a" * 64),
            report_path=str(tmp_path / "missing.json"),
        )


def test_pass_without_artifact_subject_is_rejected(tmp_path):
    report = make_report(tmp_path)

    with pytest.raises(ValueError, match="artifact_subject"):
        make_result(report_path=str(report))


def test_pass_without_report_is_rejected():
    with pytest.raises(ValueError, match="report_path"):
        make_result(
            artifact_subject="sha256:" + ("a" * 64),
        )


def test_pass_with_nonzero_exit_code_is_rejected(tmp_path):
    report = make_report(tmp_path)

    with pytest.raises(ValueError, match="raw_exit_code"):
        make_result(
            raw_exit_code=2,
            artifact_subject="sha256:" + ("a" * 64),
            report_path=str(report),
        )


def test_success_with_error_exit_code_is_rejected():
    with pytest.raises(ValueError, match="raw_exit_code"):
        make_result(raw_exit_code=2)


def test_success_without_exit_code_is_rejected():
    with pytest.raises(ValueError, match="raw_exit_code"):
        make_result(raw_exit_code=None)


def test_boolean_exit_code_is_rejected():
    with pytest.raises(ValueError, match="raw_exit_code"):
        make_result(raw_exit_code=True)


def test_empty_artifact_subject_is_rejected(tmp_path):
    report = make_report(tmp_path)

    with pytest.raises(ValueError, match="artifact_subject"):
        make_result(
            artifact_subject=" ",
            report_path=str(report),
        )


def make_trivy_report(tmp_path, digest=None):
    digest = digest or ("a" * 64)
    report = tmp_path / "trivy-report.json"
    report.write_text(
        json.dumps({
            "SchemaVersion": 2,
            "ArtifactName": "localhost:5000/order-app:v1.0.0",
            "ArtifactType": "container_image",
            "Metadata": {
                "RepoDigests": [
                    "localhost:5000/order-app@sha256:" + digest
                ]
            },
            "Results": [{"Target": "fixture-image-scan", "Vulnerabilities": []}],
        }),
        encoding="utf-8",
    )
    return report


def test_vulnerability_adapter_accepts_valid_matching_report(tmp_path):
    report = make_trivy_report(tmp_path)
    result = make_result(
        control_id="VULNERABILITY",
        expected_artifact="localhost:5000/order-app:v1.0.0",
        artifact_subject="sha256:" + ("a" * 64),
        report_path=str(report),
    )
    assert result["policy_verdict"] == "PASS"


def test_vulnerability_adapter_rejects_invalid_json(tmp_path):
    report = tmp_path / "invalid-trivy.json"
    report.write_text("{invalid json", encoding="utf-8")

    with pytest.raises(ValueError, match="INVALID_JSON"):
        make_result(
            control_id="VULNERABILITY",
        expected_artifact="localhost:5000/order-app:v1.0.0",
            artifact_subject="sha256:" + ("a" * 64),
            report_path=str(report),
        )


def test_vulnerability_adapter_rejects_digest_mismatch(tmp_path):
    report = make_trivy_report(tmp_path, digest="b" * 64)

    with pytest.raises(ValueError, match="DIGEST_MISMATCH"):
        make_result(
            control_id="VULNERABILITY",
        expected_artifact="localhost:5000/order-app:v1.0.0",
            artifact_subject="sha256:" + ("a" * 64),
            report_path=str(report),
        )


def test_vulnerability_adapter_rejects_missing_results(tmp_path):
    report = tmp_path / "missing-results.json"
    report.write_text(
        json.dumps({
            "SchemaVersion": 2,
            "ArtifactName": "localhost:5000/order-app:v1.0.0",
            "ArtifactType": "container_image",
            "Metadata": {
                "RepoDigests": [
                    "localhost:5000/order-app@sha256:" + ("a" * 64)
                ]
            },
        }),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="RESULTS_INVALID"):
        make_result(
            control_id="VULNERABILITY",
        expected_artifact="localhost:5000/order-app:v1.0.0",
            artifact_subject="sha256:" + ("a" * 64),
            report_path=str(report),
        )


def test_cli_rejects_pass_when_tool_exit_code_is_nonzero(tmp_path):
    import subprocess
    import sys

    output = tmp_path / "result.json"
    report = make_trivy_report(tmp_path)

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/m4_result_adapter.py",
            "--control", "VULNERABILITY",
            "--execution-status", "SUCCESS",
            "--verdict", "PASS",
            "--reason", "POLICY_SATISFIED",
            "--run-id", "cli-error-test",
            "--source-snapshot", "git:test",
            "--tool-name", "trivy",
            "--tool-version", "test",
            "--exit-code", "2",
            "--artifact-subject", "sha256:" + ("a" * 64),
            "--expected-artifact", "localhost:5000/order-app:v1.0.0",
            "--expected-report-sha256", hashlib.sha256(report.read_bytes()).hexdigest(),
            "--report", str(report),
            "--output", str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert output.is_file()
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["execution_status"] == "ERROR"
    assert result["policy_verdict"] == "ERROR"


def test_cli_writes_error_when_vulnerability_report_is_invalid(tmp_path):
    import subprocess
    import sys

    output = tmp_path / "result.json"
    report = tmp_path / "invalid-trivy.json"
    report.write_text("{invalid json", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/m4_result_adapter.py",
            "--control", "VULNERABILITY",
            "--execution-status", "SUCCESS",
            "--verdict", "PASS",
            "--reason", "POLICY_SATISFIED",
            "--run-id", "cli-invalid-report-test",
            "--source-snapshot", "git:test",
            "--tool-name", "trivy",
            "--tool-version", "test",
            "--exit-code", "0",
            "--artifact-subject", "sha256:" + ("a" * 64),
            "--expected-artifact", "localhost:5000/order-app:v1.0.0",
            "--expected-report-sha256", hashlib.sha256(report.read_bytes()).hexdigest(),
            "--report", str(report),
            "--output", str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert output.is_file()
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["execution_status"] == "ERROR"
    assert result["policy_verdict"] == "ERROR"
