#!/usr/bin/env python3
"""Generate and validate an SPDX SBOM from a local Docker image."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMAGE = "localhost:5000/order-app:v1.0.0"
DEFAULT_OUTPUT = ROOT / "bang-chung/m4/sbom"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        result = subprocess.CompletedProcess(command, 127, "", str(exc))
        result.execution_started = False
        return result


def write_evidence(path: Path, values: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(f"{key}={value}\n" for key, value in values.items()),
        encoding="utf-8",
    )


def fail_evidence(path: Path, image: str, reason: str,
                  artifact_subject: str = "UNAVAILABLE",
                  image_id: str = "UNAVAILABLE") -> None:
    write_evidence(path, {
        "SBOM_STATUS": "ERROR",
        "IMAGE": image,
        "IMAGE_ID": image_id,
        "ARTIFACT_SUBJECT": artifact_subject,
        "SBOM_PATH": str(path.parent / "order-app.spdx.json"),
        "SBOM_SHA256": "UNAVAILABLE",
        "REASON": reason,
        "TIMESTAMP_UTC": datetime.now(timezone.utc).isoformat(),
    })


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate an SPDX SBOM from a local Docker image."
    )
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    image = args.image.strip()
    if not image:
        parser.error("--image must not be empty")

    output_dir = Path(args.output_dir).resolve()
    sbom_path = output_dir / "order-app.spdx.json"
    evidence_path = output_dir / "sbom-evidence.txt"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Never reuse an old report or a stale PASS after a failed run.
    sbom_path.unlink(missing_ok=True)
    fail_evidence(evidence_path, image, "SBOM generation has not completed.")

    inspect = run(["docker", "image", "inspect", image])
    if inspect.returncode != 0:
        reason = "DOCKER_IMAGE_INSPECT_FAILED"
        print("SBOM_STATUS=ERROR")
        print(f"REASON={reason}")
        print((inspect.stderr or inspect.stdout).strip(), file=sys.stderr)
        fail_evidence(evidence_path, image, reason)
        return 2

    try:
        inspected = json.loads(inspect.stdout)
        if not isinstance(inspected, list) or not inspected:
            raise ValueError("Docker inspect returned no image")

        image_info = inspected[0]
        image_id = image_info.get("Id")
        repo_tags = image_info.get("RepoTags") or []
        repo_digests = image_info.get("RepoDigests") or []

        if not isinstance(image_id, str) or not re.fullmatch(
            r"sha256:[0-9a-f]{64}", image_id
        ):
            raise ValueError("Docker image ID is missing or invalid")

        if image not in (repo_digests if '@' in image else repo_tags):
            raise ValueError(
                f"Requested image tag {image!r} not found in Docker RepoTags"
            )

        if not isinstance(repo_digests, list) or not repo_digests:
            raise ValueError("Docker RepoDigests is missing")

        # Match repository names without splitting on ':'; registry ports
        # such as localhost:5000 are part of the repository name.
        matching_digest = None
        for entry in repo_digests:
            if not isinstance(entry, str) or "@" not in entry:
                continue
            repository, digest = entry.rsplit("@", 1)
            if (
                repository == (image.split("@")[0] if "@" in image else image.rsplit(":", 1)[0])
                and re.fullmatch(r"sha256:[0-9a-f]{64}", digest)
                and ("@" not in image or entry == image)
            ):
                matching_digest = digest
                break

        if matching_digest is None:
            raise ValueError(
                "No valid RepoDigest was associated with the requested image"
            )

        artifact_subject = matching_digest

    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        reason = f"IMAGE_IDENTITY_INVALID: {exc}"
        print("SBOM_STATUS=ERROR")
        print(f"REASON={reason}")
        fail_evidence(evidence_path, image, reason)
        return 2

    version_result = run(["syft", "version"])
    version_output = (
        (version_result.stdout or "") + "\n" + (version_result.stderr or "")
    ).strip()
    syft_version = "UNAVAILABLE"
    if version_result.returncode == 0 and version_output:
        version_lines = [
            line.strip() for line in version_output.splitlines() if line.strip()
        ]
        version_line = next(
            (line for line in version_lines if line.lower().startswith("version:")),
            "",
        )
        if version_line:
            syft_version = version_line.split(":", 1)[1].strip() or "UNAVAILABLE"

    command = ["syft", image, "-o", f"spdx-json={sbom_path}"]
    result = run(command)

    execution = {
        "command": command,
        "raw_exit_code": (
            result.returncode
            if getattr(result, "execution_started", True) is not False
            else None
        ),
        "tool": {"name": "syft", "version": syft_version},
        "stdout": result.stdout,
        "stderr": result.stderr,
        "image_reference": image,
        "artifact_subject": artifact_subject,
        "report_path": sbom_path.name,
        "report_sha256": (
            sha256_file(sbom_path) if sbom_path.is_file() else None
        ),
    }
    (output_dir / "syft-execution.json").write_text(
        json.dumps(execution, indent=2) + "\n", encoding="utf-8"
    )

    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)

    if result.returncode != 0 or not sbom_path.is_file():
        reason = (
            f"SYFT_EXECUTION_FAILED: exit={result.returncode}; "
            "report missing or command failed"
        )
        print("SBOM_STATUS=ERROR")
        print(f"REASON={reason}")
        write_evidence(evidence_path, {
            "SBOM_STATUS": "ERROR",
            "IMAGE": image,
            "IMAGE_ID": image_id,
            "ARTIFACT_SUBJECT": artifact_subject,
            "SBOM_PATH": str(sbom_path),
            "SBOM_SHA256": "UNAVAILABLE",
            "SYFT_VERSION": syft_version,
            "SYFT_EXIT_CODE": result.returncode,
            "REASON": reason,
            "TIMESTAMP_UTC": datetime.now(timezone.utc).isoformat(),
        })
        return 2

    try:
        sbom = json.loads(sbom_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        reason = f"SPDX_JSON_INVALID: {exc}"
        print("SBOM_STATUS=ERROR")
        print(f"REASON={reason}")
        fail_evidence(evidence_path, image, reason, artifact_subject, image_id)
        return 2

    from m4_result_adapter import validate_spdx
    try:
        validate_spdx(sbom)
        valid_structure = True
    except ValueError:
        valid_structure = False
    if not valid_structure:
        reason = "SPDX_STRUCTURE_INVALID_OR_NO_PACKAGES"
        print("SBOM_STATUS=FAIL")
        print(f"REASON={reason}")
        write_evidence(evidence_path, {
            "SBOM_STATUS": "FAIL",
            "IMAGE": image,
            "IMAGE_ID": image_id,
            "ARTIFACT_SUBJECT": artifact_subject,
            "SBOM_PATH": str(sbom_path),
            "SBOM_SHA256": "UNAVAILABLE",
            "REASON": reason,
            "TIMESTAMP_UTC": datetime.now(timezone.utc).isoformat(),
        })
        return 1

    report_sha256 = sha256_file(sbom_path)
    write_evidence(evidence_path, {
        "SBOM_STATUS": "PASS",
        "IMAGE": image,
        "IMAGE_ID": image_id,
        "ARTIFACT_SUBJECT": artifact_subject,
        "SBOM_FORMAT": sbom["spdxVersion"],
        "PACKAGE_COUNT": len(sbom["packages"]),
        "SBOM_PATH": str(sbom_path),
        "SBOM_SHA256": report_sha256,
        "SYFT_VERSION": syft_version,
        "TIMESTAMP_UTC": datetime.now(timezone.utc).isoformat(),
    })

    print(f"IMAGE={image}")
    print(f"IMAGE_ID={image_id}")
    print(f"ARTIFACT_SUBJECT={artifact_subject}")
    print(f"SBOM_PATH={sbom_path}")
    print(f"SBOM_SHA256={report_sha256}")
    print(f"PACKAGE_COUNT={len(sbom['packages'])}")
    print("SBOM_STATUS=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
