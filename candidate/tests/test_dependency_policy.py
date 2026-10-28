
import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "dependency_policy.py"

spec = importlib.util.spec_from_file_location(
    "dependency_policy", MODULE_PATH
)
dependency_policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dependency_policy)


class ParseRequirementsTests(unittest.TestCase):
    def parse_text(self, content):
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = Path(temp_dir) / "requirements.txt"
            manifest.write_text(content, encoding="utf-8")
            return dependency_policy.parse_requirements(manifest)

    def test_accepts_exact_pins_and_ignores_comments(self):
        result = self.parse_text(
            "# direct dependencies\n"
            "Flask==3.1.2\n"
            "psycopg==3.2.10\n"
        )
        self.assertEqual(
            [(name, version) for name, version, _ in result],
            [("flask", "3.1.2"), ("psycopg", "3.2.10")],
        )

    def test_rejects_unpinned_dependency(self):
        with self.assertRaises(ValueError):
            self.parse_text("Flask\n")

    def test_rejects_version_range(self):
        with self.assertRaises(ValueError):
            self.parse_text("Flask>=3.1.2\n")

    def test_rejects_malformed_line(self):
        with self.assertRaises(ValueError):
            self.parse_text("this is not a requirement\n")

    def test_empty_manifest_is_not_accepted_as_valid_input(self):
        with self.assertRaises(ValueError):
            self.parse_text("# comments only\n")

    def test_rejects_duplicate_dependency_names(self):
        with self.assertRaises(ValueError):
            self.parse_text("Flask==3.1.2\nflask==3.1.2\n")

    def test_missing_manifest_raises_error(self):
        with self.assertRaises(FileNotFoundError):
            dependency_policy.parse_requirements(
                ROOT / "tests" / "fixtures" / "manifest-does-not-exist.txt"
            )


class DependencyPolicyCliTests(unittest.TestCase):
    def run_cli(self, manifest_content):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            manifest = temp_root / "requirements.txt"
            manifest.write_text(manifest_content, encoding="utf-8")

            policy = temp_root / "dependency-policy.yml"
            policy.write_text(
                'version: 1\n'
                'manifest:\n'
                '  path: requirements.txt\n'
                '  scope: direct\n'
                'allowlist:\n'
                '  - name: flask\n'
                '    version: "3.1.2"\n',
                encoding="utf-8",
            )

            output = io.StringIO()

            with (
                patch.object(dependency_policy, "ROOT", temp_root),
                patch.object(dependency_policy, "POLICY_FILE", policy),
                patch(
                    "sys.argv",
                    [
                        "dependency_policy.py",
                        "--manifest",
                        str(manifest),
                    ],
                ),
                contextlib.redirect_stdout(output),
            ):
                try:
                    exit_code = dependency_policy.main()
                except SystemExit as exc:
                    exit_code = exc.code

            return exit_code, output.getvalue()

    def test_unapproved_dependency_fails(self):
        exit_code, output = self.run_cli("requests==2.32.0\n")

        self.assertEqual(exit_code, 1)
        self.assertIn("DEPENDENCY_STATUS=FAIL", output)
        self.assertIn(
            "unapproved dependency: requests==2.32.0",
            output,
        )

    def test_approved_dependency_passes(self):
        exit_code, output = self.run_cli("Flask==3.1.2\n")

        self.assertEqual(exit_code, 0)
        self.assertIn("DEPENDENCY_STATUS=PASS", output)

    def test_unapproved_version_fails(self):
        exit_code, output = self.run_cli("Flask==3.1.1\n")

        self.assertEqual(exit_code, 1)
        self.assertIn("DEPENDENCY_STATUS=FAIL", output)
        self.assertIn("version not approved", output)


if __name__ == "__main__":
    unittest.main()
