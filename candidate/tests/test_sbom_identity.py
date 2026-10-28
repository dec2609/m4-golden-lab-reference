
import hashlib
import json
import tempfile
import unittest
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_sbom_identity(
    archive_path: Path,
    expected_sha256: str,
    sbom_path: Path,
) -> tuple[bool, str]:
    """Validate archive bytes and basic CycloneDX structure.

    The expected hash must be supplied explicitly. This function does not
    infer or copy an image digest from historical M3 evidence.
    """
    if not archive_path.is_file():
        return False, "ARCHIVE_MISSING"

    if not expected_sha256 or len(expected_sha256) != 64:
        return False, "EXPECTED_SHA256_INVALID"

    actual_sha256 = sha256_file(archive_path)
    if actual_sha256.lower() != expected_sha256.lower():
        return False, "ARCHIVE_SHA256_MISMATCH"

    if not sbom_path.is_file():
        return False, "SBOM_MISSING"

    try:
        data = json.loads(sbom_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, "SBOM_INVALID_JSON"

    if data.get("bomFormat") != "CycloneDX":
        return False, "SBOM_FORMAT_INVALID"

    if not isinstance(data.get("components"), list):
        return False, "SBOM_COMPONENTS_INVALID"

    if not data["components"]:
        return False, "SBOM_COMPONENTS_EMPTY"

    return True, "STRUCTURE_VALID"


class SbomIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.archive = self.root / "test-artifact.tar"
        self.archive.write_bytes(b"self-sourced M4 test artifact")
        self.expected_hash = sha256_file(self.archive)
        self.sbom = self.root / "sbom.json"
        self.sbom.write_text(
            json.dumps({
                "bomFormat": "CycloneDX",
                "specVersion": "1.6",
                "version": 1,
                "components": [
                    {"type": "library", "name": "example", "version": "1.0"}
                ],
            }),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_accepts_matching_archive_and_cyclonedx_structure(self):
        ok, reason = validate_sbom_identity(
            self.archive, self.expected_hash, self.sbom
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "STRUCTURE_VALID")

    def test_rejects_wrong_archive_hash(self):
        ok, reason = validate_sbom_identity(
            self.archive, "0" * 64, self.sbom
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "ARCHIVE_SHA256_MISMATCH")

    def test_rejects_missing_archive(self):
        ok, reason = validate_sbom_identity(
            self.root / "missing.tar", self.expected_hash, self.sbom
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "ARCHIVE_MISSING")

    def test_rejects_missing_sbom(self):
        ok, reason = validate_sbom_identity(
            self.archive, self.expected_hash, self.root / "missing.json"
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "SBOM_MISSING")

    def test_rejects_malformed_sbom_json(self):
        self.sbom.write_text("{not-json", encoding="utf-8")
        ok, reason = validate_sbom_identity(
            self.archive, self.expected_hash, self.sbom
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "SBOM_INVALID_JSON")

    def test_rejects_empty_components(self):
        self.sbom.write_text(
            json.dumps({"bomFormat": "CycloneDX", "components": []}),
            encoding="utf-8",
        )
        ok, reason = validate_sbom_identity(
            self.archive, self.expected_hash, self.sbom
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "SBOM_COMPONENTS_EMPTY")


if __name__ == "__main__":
    unittest.main()
