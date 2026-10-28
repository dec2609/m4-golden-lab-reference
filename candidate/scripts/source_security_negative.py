#!/usr/bin/env python3
import os
import sys
import tempfile
import subprocess
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GITLEAKS_BIN = ROOT / "bin" / "gitleaks"

def test_negative_sandbox():
    if not GITLEAKS_BIN.exists():
        print("[ERROR] Gitleaks binary not found. Run source_security.py first.")
        sys.exit(1)

    print("[*] Creating isolated sandbox for Negative Testing...")
    sandbox_dir = tempfile.mkdtemp(prefix="m4_gitleaks_sandbox_")

    try:
        subprocess.run(["git", "init"], cwd=sandbox_dir, capture_output=True, check=True)

        dummy_secret = "AKIAIOS" + "FODNN7EXAMPLE"
        secret_file = os.path.join(sandbox_dir, "config.yml")
        with open(secret_file, "w") as f:
            f.write(f"aws_access_key_id: {dummy_secret}\n")

        subprocess.run(["git", "add", "."], cwd=sandbox_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Inject dummy secret"], cwd=sandbox_dir, capture_output=True)

        print("[*] Running Gitleaks on sandbox...")
        report_path = os.path.join(sandbox_dir, "report.json")
        cmd = [
            str(GITLEAKS_BIN), "detect",
            "--source", sandbox_dir,
            "--redact",
            "--report-path", report_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        assert result.returncode == 1, f"Expected exit code 1, got {result.returncode}"

        with open(report_path, "r") as f:
            report_data = f.read()
            assert dummy_secret not in report_data, "Redact failed! Secret exposed in report."
            assert "REDACTED" in report_data, "Report does not contain REDACTED mask."

        print("[PASS] Negative Test: Gitleaks successfully detected synthetic secret and redacted the output.")
        print("[*] GITLEAKS_STATUS=FAIL (Expected behavior in negative test)")

    except AssertionError as e:
        print(f"[FAIL] Negative Test failed: {e}")
        sys.exit(1)
    finally:
        shutil.rmtree(sandbox_dir)
        print("[*] Sandbox cleaned up.")

if __name__ == "__main__":
    test_negative_sandbox()