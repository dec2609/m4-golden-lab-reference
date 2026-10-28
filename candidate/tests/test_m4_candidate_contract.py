import json
import subprocess
from pathlib import Path

import pytest

from scripts.m4_result_adapter import (
    _contract_check_current_context,
    _contract_validate_dependency,
    candidate,
    checkout_snapshot,
    git_commit_snapshot,
    producer_checkout_snapshot,
    emit_control,
    load_context,
    validate_control,
    validate_spdx,
    validate_trivy,
)


def make_checkout(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "contract-test@example.invalid"],
        cwd=root, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "M4 contract test"],
        cwd=root, check=True,
    )

    files = {
        "scripts/app.py": "VALUE = 1\n",
        "tests/test_sample.py": "def test_sample():\n    assert True\n",
        "ma-nguon/order-app/requirements.txt": "Flask==3.1.2\n",
        "cau-hinh/m4/dependency-policy.yml": "version: 1\n",
        "Makefile": "test:\n\t@true\n",
        "docker-compose.yml": "services: {}\n",
        "bang-chung/evidence.txt": "excluded from snapshot\n",
    }
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "fixture"],
        cwd=root, check=True,
    )
    return root


def make_candidate(root, run_id="run_001"):
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    digest = "sha256:" + "a" * 64
    return {
        "contract": "reference-1",
        "source_commit": commit,
        "source_snapshot": checkout_snapshot(root),
        "run_id": run_id,
        "archive_sha256": "b" * 64,
        "manifest_digest": digest,
        "platform_manifest_digest": "sha256:" + "d" * 64,
        "config_digest": "sha256:" + "c" * 64,
        "artifact_subject": digest,
        "image_reference": "registry.invalid/order-app@" + digest,
        "archive_path": "archive/order-app.tar",
        "registry_manifest_path": "registry/manifest.json",
        "public_key_path": "cosign.pub",
        "bundle_path": "signature-bundle.json",
    }


def test_candidate_rejects_mutable_image_reference(tmp_path):
    root = make_checkout(tmp_path)
    value = make_candidate(root)
    value["image_reference"] = "registry.invalid/order-app:latest"
    with pytest.raises(ValueError, match="IMAGE_REFERENCE_NOT_IMMUTABLE"):
        candidate(value)


def test_candidate_rejects_path_traversal(tmp_path):
    root = make_checkout(tmp_path)
    value = make_candidate(root)
    value["archive_path"] = "../order-app.tar"
    with pytest.raises(ValueError, match="CANDIDATE_PATH_INVALID"):
        candidate(value)


def test_load_context_binds_commit_and_snapshot(tmp_path):
    root = make_checkout(tmp_path)
    run_dir = tmp_path / "run_001"
    run_dir.mkdir()
    value = make_candidate(root)
    candidate_file = run_dir / "candidate.json"
    candidate_file.write_text(json.dumps(value), encoding="utf-8")

    loaded = load_context(candidate_file, root)
    assert loaded["source_commit"] == value["source_commit"]
    assert loaded["source_snapshot"] == value["source_snapshot"]

    (root / "scripts/app.py").write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="SOURCE_SNAPSHOT_MISMATCH"):
        load_context(candidate_file, root)



def test_candidate_requires_platform_manifest_digest(tmp_path):
    root = make_checkout(tmp_path)
    value = make_candidate(root)
    value.pop("platform_manifest_digest")
    with pytest.raises(ValueError, match="PLATFORM_MANIFEST_DIGEST_INVALID"):
        candidate(value)


def test_load_context_accepts_historical_source_commit(tmp_path):
    root = make_checkout(tmp_path)
    source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    source_snapshot = git_commit_snapshot(root, source_commit)

    app = root / "scripts/app.py"
    app.write_text("VALUE = 2\n", encoding="utf-8")
    subprocess.run(["git", "add", "scripts/app.py"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "next source revision"],
        cwd=root, check=True,
    )

    run_dir = tmp_path / "historical_run"
    run_dir.mkdir()
    value = make_candidate(root, run_id="historical_run")
    value["source_commit"] = source_commit
    value["source_snapshot"] = source_snapshot
    candidate_file = run_dir / "candidate.json"
    candidate_file.write_text(json.dumps(value), encoding="utf-8")

    loaded = load_context(candidate_file, root)
    assert loaded["source_commit"] == source_commit
    assert loaded["source_snapshot"] == source_snapshot

def test_snapshot_ignores_out_of_scope_file_changes(tmp_path):
    root = make_checkout(tmp_path)
    before = checkout_snapshot(root)
    (root / "bang-chung/evidence.txt").write_text(
        "different evidence\n", encoding="utf-8"
    )
    assert checkout_snapshot(root) == before


def test_spdx_rejects_empty_packages():
    with pytest.raises(ValueError, match="SPDX_PACKAGES_EMPTY_OR_INVALID"):
        validate_spdx({
            "spdxVersion": "SPDX-2.3",
            "SPDXID": "SPDXRef-DOCUMENT",
            "packages": [],
        })


def test_trivy_rejects_empty_results(tmp_path):
    root = make_checkout(tmp_path)
    context = make_candidate(root)
    report = {
        "SchemaVersion": 2,
        "ArtifactType": "container_image",
        "ArtifactName": context["image_reference"],
        "Metadata": {"RepoDigests": [context["image_reference"]]},
        "Results": [],
    }
    with pytest.raises(ValueError, match="TRIVY_RESULTS_EMPTY_OR_INVALID"):
        validate_trivy(report, context)


def test_trivy_rejects_critical_findings(tmp_path):
    root = make_checkout(tmp_path)
    context = make_candidate(root)
    report = {
        "SchemaVersion": 2,
        "ArtifactType": "container_image",
        "ArtifactName": context["image_reference"],
        "Metadata": {"RepoDigests": [context["image_reference"]]},
        "Results": [{
            "Target": "rootfs",
            "Vulnerabilities": [{
                "VulnerabilityID": "CVE-TEST-1",
                "Severity": "CRITICAL",
            }],
        }],
    }
    assert validate_trivy(report, context) is False


def test_emit_control_writes_bound_sbom_records(tmp_path):
    root = make_checkout(tmp_path)
    run_dir = tmp_path / "run_emit"
    run_dir.mkdir()
    context = make_candidate(root, run_id="run_emit")

    report = run_dir / "sbom" / "order-app.spdx.json"
    report.parent.mkdir()
    report.write_text(json.dumps({
        "spdxVersion": "SPDX-2.3",
        "SPDXID": "SPDXRef-DOCUMENT",
        "packages": [{"name": "sample-package"}],
    }), encoding="utf-8")

    result_path = emit_control(
        context=context,
        run_dir=run_dir,
        control="SBOM",
        report_path=report,
        raw_exit=0,
        verdict="PASS",
        tool={"name": "syft", "version": "test-version"},
        command=["syft", context["image_reference"], "-o", "spdx-json"],
        reason="SPDX report validated",
        wrapper_exit_code=0,
        policy_exit_code=0,
        repository_root=root,
    )

    result = json.loads(result_path.read_text(encoding="utf-8"))
    execution_path = run_dir / "sbom-execution.json"
    execution = json.loads(execution_path.read_text(encoding="utf-8"))

    assert result["schema_version"] == "1.0"
    assert result["control_id"] == "SBOM"
    assert result["execution_status"] == "SUCCESS"
    assert result["policy_verdict"] == "PASS"
    assert result["artifact_subject"] == context["manifest_digest"]
    assert result["report"]["path"] == "sbom/order-app.spdx.json"
    assert result["report"]["sha256"] == execution["report_sha256"]
    assert execution["raw_exit_code"] == 0
    assert execution["command"][0] == "syft"
    assert validate_control(run_dir, "SBOM", context, root).evidence_valid


def test_emit_control_refuses_nonzero_exit_for_pass(tmp_path):
    root = make_checkout(tmp_path)
    run_dir = tmp_path / "run_nonzero"
    run_dir.mkdir()
    context = make_candidate(root, run_id="run_nonzero")
    report = run_dir / "sbom.json"
    report.write_text(json.dumps({
        "spdxVersion": "SPDX-2.3",
        "SPDXID": "SPDXRef-DOCUMENT",
        "packages": [{"name": "sample-package"}],
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="NONZERO_RAW_EXIT_CANNOT_PASS"):
        emit_control(
            context, run_dir, "SBOM", report, 2, "PASS",
            {"name": "syft", "version": "test-version"},
            ["syft", context["image_reference"]], "must not pass",
            repository_root=root,
        )

    assert not (run_dir / "sbom-result.json").exists()
    assert not (run_dir / "sbom-execution.json").exists()


def test_validate_control_detects_report_hash_tampering(tmp_path):
    root = make_checkout(tmp_path)
    run_dir = tmp_path / "run_tamper"
    run_dir.mkdir()
    context = make_candidate(root, run_id="run_tamper")
    report = run_dir / "sbom.json"
    report.write_text(json.dumps({
        "spdxVersion": "SPDX-2.3",
        "SPDXID": "SPDXRef-DOCUMENT",
        "packages": [{"name": "sample-package"}],
    }), encoding="utf-8")

    emit_control(
        context, run_dir, "SBOM", report, 0, "PASS",
        {"name": "syft", "version": "test-version"},
        ["syft", context["image_reference"]], "SPDX report validated",
        repository_root=root,
    )
    report.write_text('{"tampered": true}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="CONTROL_REPORT_HASH_MISMATCH"):
        validate_control(run_dir, "SBOM", context, root)


def _write_dependency_policy(root):
    (root / "cau-hinh/m4/dependency-policy.yml").write_text(
        """version: 1
manifest:
  path: ma-nguon/order-app/requirements.txt
  scope: direct
rules:
  package_name_normalization: lowercase
  version_format: exact
  unapproved_dependency: fail
exceptions:
  allowed: false
  review: pull_request
allowlist:
  - name: flask
    version: "3.1.2"
""",
        encoding="utf-8",
    )


def test_dependency_contract_accepts_approved_direct_manifest(tmp_path):
    root = make_checkout(tmp_path)
    _write_dependency_policy(root)

    report = {
        "schema_version": "1.0",
        "status": "PASS",
        "reason": "ALL_DIRECT_DEPENDENCIES_APPROVED",
        "manifest": "ma-nguon/order-app/requirements.txt",
        "scope": "direct",
        "packages": [
            {"name": "flask", "version": "3.1.2", "approved": True},
        ],
        "violations": [],
    }

    _contract_validate_dependency(report, root, expected_verdict="PASS")


def test_dependency_contract_accepts_truthful_policy_failure(tmp_path):
    root = make_checkout(tmp_path)
    _write_dependency_policy(root)
    (root / "ma-nguon/order-app/requirements.txt").write_text(
        "Flask==4.0\n", encoding="utf-8"
    )

    report = {
        "schema_version": "1.0",
        "status": "FAIL",
        "reason": "DEPENDENCY_POLICY_VIOLATION",
        "manifest": "ma-nguon/order-app/requirements.txt",
        "scope": "direct",
        "packages": [
            {"name": "flask", "version": "4.0", "approved": False},
        ],
        "violations": ["version not approved: flask==4.0"],
    }

    _contract_validate_dependency(report, root, expected_verdict="FAIL")


def test_dependency_contract_rejects_false_pass(tmp_path):
    root = make_checkout(tmp_path)
    _write_dependency_policy(root)
    (root / "ma-nguon/order-app/requirements.txt").write_text(
        "Flask==4.0\n", encoding="utf-8"
    )

    report = {
        "schema_version": "1.0",
        "status": "PASS",
        "reason": "ALL_DIRECT_DEPENDENCIES_APPROVED",
        "manifest": "ma-nguon/order-app/requirements.txt",
        "scope": "direct",
        "packages": [
            {"name": "flask", "version": "4.0", "approved": True},
        ],
        "violations": [],
    }

    with pytest.raises(ValueError, match="DEPENDENCY_REPORT_APPROVAL_MISMATCH"):
        _contract_validate_dependency(report, root, expected_verdict="PASS")


def test_dependency_control_accepts_external_policy_pinned_by_hash(tmp_path):
    import hashlib
    import platform

    root = make_checkout(tmp_path)
    _write_dependency_policy(root)

    external_policy = tmp_path / "external-m4-policy.yml"
    external_policy.write_text(
        (root / "cau-hinh/m4/dependency-policy.yml").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    policy_hash = hashlib.sha256(
        external_policy.read_bytes()
    ).hexdigest()
    manifest = root / "ma-nguon/order-app/requirements.txt"
    manifest_hash = hashlib.sha256(manifest.read_bytes()).hexdigest()

    run_dir = tmp_path / "run_dep_external"
    run_dir.mkdir()
    context = make_candidate(root, run_id=run_dir.name)

    report_path = run_dir / "dependency-report.json"
    report_path.write_text(json.dumps({
        "schema_version": "1.0",
        "status": "PASS",
        "reason": "ALL_DIRECT_DEPENDENCIES_APPROVED",
        "manifest": "ma-nguon/order-app/requirements.txt",
        "manifest_sha256": manifest_hash,
        "policy_sha256": policy_hash,
        "scope": "direct",
        "packages": [
            {"name": "flask", "version": "3.1.2", "approved": True},
        ],
        "violations": [],
    }), encoding="utf-8")

    result = emit_control(
        context=context,
        run_dir=run_dir,
        control="DEPENDENCY",
        report_path=report_path,
        raw_exit=0,
        verdict="PASS",
        tool={"name": "python", "version": platform.python_version()},
        command=["python", "scripts/dependency_policy.py"],
        reason="M4 policy and source manifest verified",
        wrapper_exit_code=0,
        policy_exit_code=0,
        repository_root=root,
        dependency_policy_path=external_policy,
        expected_dependency_policy_sha256=policy_hash,
    )

    assert result.is_file()
    assert validate_control(
        run_dir,
        "DEPENDENCY",
        context,
        root,
        dependency_policy_path=external_policy,
        expected_dependency_policy_sha256=policy_hash,
    ).evidence_valid

def test_candidate_rejects_partial_producer_context(tmp_path):
    root = make_checkout(tmp_path)
    value = make_candidate(root)
    value["producer_commit"] = value["source_commit"]

    with pytest.raises(ValueError, match="PRODUCER_CONTEXT_INVALID"):
        candidate(value)


def test_producer_context_binds_historical_artifact_source_and_worktree(tmp_path):
    root = make_checkout(tmp_path)

    artifact_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    artifact_snapshot = git_commit_snapshot(root, artifact_commit)

    app = root / "scripts/app.py"
    app.write_text("VALUE = 2\n", encoding="utf-8")
    subprocess.run(["git", "add", "scripts/app.py"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "change producer source"],
        cwd=root, check=True,
    )
    producer_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()

    value = make_candidate(root, run_id="producer_binding_test")
    value["source_commit"] = artifact_commit
    value["source_snapshot"] = artifact_snapshot
    value["producer_commit"] = producer_commit
    value["producer_snapshot"] = producer_checkout_snapshot(root)

    _contract_check_current_context(value, root)

    # New in-scope source must invalidate the bound producer snapshot.
    (root / "scripts/new_runner_file.py").write_text(
        "PRODUCER_VALUE = True\n", encoding="utf-8"
    )
    with pytest.raises(
        ValueError, match="PRODUCER_CHECKOUT_SNAPSHOT_MISMATCH"
    ):
        _contract_check_current_context(value, root)
