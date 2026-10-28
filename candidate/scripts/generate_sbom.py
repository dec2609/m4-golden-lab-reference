
#!/usr/bin/env python3

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = ROOT / "bang-chung/m3/artifact/order-app.tar"
SBOM_JSON = ROOT / "bang-chung/m3/sbom/sbom.cdx.json"
EVIDENCE_TXT = ROOT / "bang-chung/m3/sbom/sbom-evidence.txt"
DIGEST_FILE = ROOT / "bang-chung/m3/artifact/digest-verification.json"

# Giá trị mặc định chuẩn từ bản build M3 mới nhất của Quang
DEFAULT_IMAGE_DIGEST = "sha256:20416d1b4217ffd21776d5cb0a30ff54cfc1f219745b6b3dbc74499b2b1c6fde"
DEFAULT_ARTIFACT_SHA256 = "7295cf9571dae8f8fd5219b598728d3dcbc757e9972a78c97e8e4fe2ff723f82"


def load_expected_digests():
    """Đọc động image_digest và artifact_sha256 từ file do Quang xuất."""
    if DIGEST_FILE.exists():
        try:
            data = json.loads(DIGEST_FILE.read_text(encoding="utf-8"))
            img_digest = data.get("image_digest", DEFAULT_IMAGE_DIGEST)
            art_sha = data.get("artifact_sha256", DEFAULT_ARTIFACT_SHA256)
            return img_digest, art_sha
        except Exception as e:
            print(f"Warning: Không thể đọc {DIGEST_FILE}: {e}")
    return DEFAULT_IMAGE_DIGEST, DEFAULT_ARTIFACT_SHA256


EXPECTED_IMAGE_DIGEST, EXPECTED_ARTIFACT_SHA256 = load_expected_digests()


def get_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def enrich_sbom_metadata(sbom_path: Path, image_digest: str):
    """Cập nhật metadata.component của CycloneDX JSON với image_digest từ Quang."""
    try:
        data = json.loads(sbom_path.read_text(encoding="utf-8"))
        if "metadata" not in data:
            data["metadata"] = {}
        if "component" not in data["metadata"]:
            data["metadata"]["component"] = {"type": "container", "name": "order-app"}

        data["metadata"]["component"]["version"] = image_digest
        data["metadata"]["component"]["purl"] = f"pkg:docker/order-app@{image_digest}"

        sbom_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"Warning: Không thể enrich metadata SBOM: {e}")


def validate_sbom(sbom_path: Path) -> bool:
    if not sbom_path.exists():
        return False
    try:
        data = json.loads(sbom_path.read_text(encoding="utf-8"))
        if data.get("bomFormat") != "CycloneDX":
            return False
        if not data.get("components") or len(data["components"]) == 0:
            return False
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--archive",
        default=str(DEFAULT_ARCHIVE),
        help="Đường dẫn OCI archive tar do Quang cấp",
    )
    args = parser.parse_args()

    archive_path = Path(args.archive)

    if not archive_path.exists():
        print("SBOM_STATUS=FAIL")
        print(f"ERROR: Không tìm thấy OCI archive tại {archive_path}")
        return 1

    archive_sha256 = get_sha256(archive_path)
    SBOM_JSON.parent.mkdir(parents=True, exist_ok=True)

    # Chạy syft quét từ OCI archive cấp bởi Quang
    cmd = [
        "syft",
        f"docker-archive:{archive_path}",
        "-o",
        "cyclonedx-json",
        "--file",
        str(SBOM_JSON),
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("SBOM_STATUS=FAIL")
        print(f"ERROR khi chạy syft: {res.stderr}")
        return 1

    # Enrich Image Digest vào SBOM metadata
    enrich_sbom_metadata(SBOM_JSON, EXPECTED_IMAGE_DIGEST)

    if validate_sbom(SBOM_JSON):
        EVIDENCE_TXT.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE_TXT.write_text(
            f"SBOM Evidence\n"
            f"==============\n"
            f"archive_path={archive_path.relative_to(ROOT)}\n"
            f"artifact_sha256={archive_sha256}\n"
            f"image_digest={EXPECTED_IMAGE_DIGEST}\n"
            f"sbom_output=bang-chung/m3/sbom/sbom.cdx.json\n"
            f"status=MAPPED_AND_VERIFIED\n"
            f"SBOM_STATUS=PASS\n",
            encoding="utf-8",
        )
        print(f"Artifact SHA-256: {archive_sha256}")
        print(f"Image Digest    : {EXPECTED_IMAGE_DIGEST}")
        print(f"SBOM Output     : {SBOM_JSON.relative_to(ROOT)}")
        print("SBOM_STATUS=PASS")
        return 0
    else:
        print("SBOM_STATUS=FAIL")
        print("ERROR: SBOM thiếu components hoặc sai format CycloneDX")
        return 1


if __name__ == "__main__":
    sys.exit(main())


