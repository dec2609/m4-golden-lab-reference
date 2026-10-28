import sys, os, json, unittest, tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))
import source_security

class TestSourceSecurityAdapter(unittest.TestCase):
    def setUp(self):
        self.context = patch("source_security.get_repo_context", return_value=("a"*40, False))
        self.context.start()
        self.addCleanup(self.context.stop)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_evidence_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def get_manifest(self):
        with open(self.test_evidence_dir / "run_manifest.json") as f:
            return json.load(f)

    @patch('source_security.install_and_verify_gitleaks', return_value=False)
    def test_bad_checksum_rejects_binary(self, mock_install):
        self.assertFalse(source_security.run_scan(self.test_evidence_dir))
        self.assertEqual(self.get_manifest()["GITLEAKS_STATUS"], "FAIL")

    @patch('source_security.install_and_verify_gitleaks', return_value=True)
    @patch('subprocess.run')
    def test_exit_0_but_has_findings_is_fail(self, mock_run, mock_install):
        def side_effect(cmd, **kwargs):
            with open(cmd[cmd.index("--report-path") + 1], "w") as f:
                json.dump([{"Description": "Leak"}], f)
            return MagicMock(returncode=0)
        mock_run.side_effect = side_effect
        self.assertFalse(source_security.run_scan(self.test_evidence_dir))
        self.assertEqual(self.get_manifest()["GITLEAKS_STATUS"], "FAIL")
        self.assertIn("1 finding", self.get_manifest()["reason"])

    @patch('source_security.install_and_verify_gitleaks', return_value=True)
    @patch('subprocess.run')
    def test_exit_0_but_empty_report_is_fail(self, mock_run, mock_install):
        def side_effect(cmd, **kwargs):
            open(cmd[cmd.index("--report-path") + 1], "w").close()
            return MagicMock(returncode=0)
        mock_run.side_effect = side_effect
        self.assertFalse(source_security.run_scan(self.test_evidence_dir))
        self.assertEqual(self.get_manifest()["GITLEAKS_STATUS"], "FAIL")

    @patch('source_security.install_and_verify_gitleaks', return_value=True)
    @patch('subprocess.run')
    def test_clean_scan_is_pass(self, mock_run, mock_install):
        def side_effect(cmd, **kwargs):
            with open(cmd[cmd.index("--report-path") + 1], "w") as f:
                json.dump([], f)
            return MagicMock(returncode=0)
        mock_run.side_effect = side_effect
        self.assertTrue(source_security.run_scan(self.test_evidence_dir))
        self.assertEqual(self.get_manifest()["GITLEAKS_STATUS"], "PASS")

if __name__ == '__main__':
    unittest.main()