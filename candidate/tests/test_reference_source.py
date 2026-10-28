import hashlib, io, json, tarfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
import source_security as scanner

def pinned_archive(tmp_path, monkeypatch):
    binary = b'CONTRACT FIXTURE EXECUTABLE - NOT RUN'
    archive = tmp_path / 'gl.tgz'
    with tarfile.open(archive, 'w:gz') as t:
        member = tarfile.TarInfo('gitleaks'); member.size = len(binary); t.addfile(member, io.BytesIO(binary))
    monkeypatch.setattr(scanner, 'BIN_DIR', tmp_path); monkeypatch.setattr(scanner, 'GITLEAKS_BIN', tmp_path / 'gitleaks'); monkeypatch.setattr(scanner, 'GITLEAKS_ARCHIVE_SHA256', hashlib.sha256(archive.read_bytes()).hexdigest())
    monkeypatch.setattr(scanner.platform, 'system', lambda: 'Linux'); monkeypatch.setattr(scanner.platform, 'machine', lambda: 'x86_64')
    return binary, archive

def test_archive_and_executable_checksums_are_distinct(tmp_path, monkeypatch):
    binary, archive = pinned_archive(tmp_path, monkeypatch)
    assert hashlib.sha256(binary).hexdigest() != scanner.GITLEAKS_ARCHIVE_SHA256
    with patch.object(scanner.subprocess, 'run', return_value=Mock(returncode=0, stdout='8.18.4', stderr='')):
        assert scanner.install_and_verify_gitleaks()
        assert scanner.verify_binary_integrity() and scanner.ACTUAL_VERSION == '8.18.4'
    scanner.GITLEAKS_BIN.write_bytes(b'corrupt')
    assert not scanner.verify_binary_integrity()
    with patch.object(scanner.subprocess, 'run') as run: assert not scanner.install_and_verify_gitleaks(); run.assert_not_called()

def test_archive_tampering_rejected(tmp_path, monkeypatch):
    _, archive = pinned_archive(tmp_path, monkeypatch); archive.write_bytes(b'corrupt')
    assert not scanner.install_and_verify_gitleaks()

def test_actual_version_mismatch_rejected(tmp_path, monkeypatch):
    pinned_archive(tmp_path, monkeypatch)
    with patch.object(scanner.subprocess, 'run', return_value=Mock(returncode=0, stdout='unknown', stderr='')): assert not scanner.install_and_verify_gitleaks()

@pytest.mark.parametrize('head,dirty', [('UNKNOWN', False), ('a'*40, True), ('0'*40, False)])
def test_source_context_fail_closed(tmp_path, head, dirty):
    with patch.object(scanner, 'get_repo_context', return_value=(head, dirty)), patch.object(scanner, 'install_and_verify_gitleaks') as installer:
        assert not scanner.run_scan(tmp_path); installer.assert_not_called()
    assert json.loads((tmp_path / 'run_manifest.json').read_text())['GITLEAKS_STATUS'] == 'FAIL'

@pytest.mark.parametrize('code,payload', [(0, [{'RuleID': 'fixture'}]), (2, []), (0, {}), (0, None), (1, [])])
def test_scan_negatives(tmp_path, code, payload):
    def run(cmd, **kw):
        report = Path(cmd[cmd.index('--report-path') + 1])
        if payload is not None: report.write_text(json.dumps(payload))
        return Mock(returncode=code)
    with patch.object(scanner, 'get_repo_context', return_value=('a'*40, False)), patch.object(scanner, 'install_and_verify_gitleaks', return_value=True), patch.object(scanner.subprocess, 'run', side_effect=run): assert not scanner.run_scan(tmp_path)

def test_both_history_and_worktree_are_scanned(tmp_path):
    calls = []
    def run(cmd, **kw): calls.append(cmd); Path(cmd[cmd.index('--report-path') + 1]).write_text('[]'); return Mock(returncode=0)
    with patch.object(scanner, 'get_repo_context', return_value=('a'*40, False)), patch.object(scanner, 'install_and_verify_gitleaks', return_value=True), patch.object(scanner.subprocess, 'run', side_effect=run): assert scanner.run_scan(tmp_path)
    assert len(calls) == 2 and '--no-git' not in calls[0] and '--no-git' in calls[1]

def test_source_change_during_scan_rejected(tmp_path):
    def run(cmd, **kw): Path(cmd[cmd.index('--report-path') + 1]).write_text('[]'); return Mock(returncode=0)
    with patch.object(scanner, 'get_repo_context', side_effect=[('a'*40, False), ('b'*40, False)]), patch.object(scanner, 'install_and_verify_gitleaks', return_value=True), patch.object(scanner.subprocess, 'run', side_effect=run): assert not scanner.run_scan(tmp_path)

def test_default_evidence_does_not_dirty_scanned_checkout(tmp_path):
    with patch.object(scanner.tempfile, 'mkdtemp', return_value=str(tmp_path)), patch.object(scanner, 'get_repo_context', return_value=('a'*40, False)), patch.object(scanner, 'install_and_verify_gitleaks', return_value=False):
        assert not scanner.run_scan()
    assert (tmp_path / 'run_manifest.json').is_file()
    assert not tmp_path.is_relative_to(scanner.ROOT)