import json
import subprocess

import pytest

from scripts import run_m4_controls as runner


@pytest.mark.parametrize(
    ("returncode", "status", "result_content"),
    [
        (2, "ERROR", {"status": "ERROR"}),
        (0, "ERROR", {"status": "PASS"}),
        (1, "PASS", {"status": "PASS"}),
        (0, "PASS", {"status": "ERROR"}),
        (0, "PASS", None),
    ],
)
def test_trivy_is_not_run_when_freshness_is_not_proven(
    tmp_path, monkeypatch, returncode, status, result_content
):
    result_path = tmp_path / "freshness.json"
    if result_content is not None:
        result_path.write_text(json.dumps(result_content), encoding="utf-8")

    calls = []
    monkeypatch.setattr(runner, "run", lambda command: calls.append(command))
    command = ["trivy", "image", "example@sha256:abc"]
    freshness_exec = subprocess.CompletedProcess(
        ["freshness-check"], returncode, "", "checker stderr"
    )

    result = runner.run_trivy_if_fresh(
        command, freshness_exec, status, result_path
    )

    assert calls == []
    assert result.returncode == 2
    assert "TRIVY_DATABASE_FRESHNESS_CHECK_FAILED" in result.stderr


def test_trivy_runs_only_when_freshness_result_is_persisted_pass(
    tmp_path, monkeypatch
):
    result_path = tmp_path / "freshness.json"
    result_path.write_text(
        json.dumps({"status": "PASS", "reason": "DATABASE_FRESH"}),
        encoding="utf-8",
    )
    command = ["trivy", "image", "example@sha256:abc"]
    expected = subprocess.CompletedProcess(command, 0, "scan ok", "")
    calls = []

    def fake_run(actual_command):
        calls.append(actual_command)
        return expected

    monkeypatch.setattr(runner, "run", fake_run)
    freshness_exec = subprocess.CompletedProcess(
        ["freshness-check"], 0, "REPRODUCIBILITY_STATUS=PASS", ""
    )

    result = runner.run_trivy_if_fresh(
        command, freshness_exec, "PASS", result_path
    )

    assert calls == [command]
    assert result is expected


def test_inspect_image_accepts_immutable_reference_without_tag(monkeypatch):
    digest = "sha256:" + "d" * 64
    image = "registry.invalid/order-app@" + digest
    inspect_data = [{
        "Id": "sha256:" + "e" * 64,
        "RepoTags": [],
        "RepoDigests": [image],
    }]

    monkeypatch.setattr(
        runner,
        "run",
        lambda command: subprocess.CompletedProcess(
            command, 0, json.dumps(inspect_data), ""
        ),
    )

    result = runner.inspect_image(image)

    assert result["image"] == image
    assert result["artifact_subject"] == digest
    assert result["repository_digest"] == image


def test_candidate_cli_fails_closed_for_missing_descriptor(
    tmp_path, monkeypatch
):
    import sys

    missing = tmp_path / "missing-candidate.json"
    output = tmp_path / "external-evidence"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_m4_controls.py",
            "--candidate", str(missing),
            "--output-dir", str(output),
        ],
    )

    assert runner.main() == 2
    assert not output.exists()
