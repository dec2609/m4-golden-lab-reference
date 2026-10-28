"""M4 Cosign API tests; doubles do not verify a signature cryptographically."""
from unittest.mock import Mock
from reference_fixture import fixture
from production_gate import verify_cosign

def test_missing_cosign(tmp_path):
 fixture(tmp_path)
 assert not verify_cosign(tmp_path/'candidate.tar',tmp_path/'cosign.pub',tmp_path/'bundle.json',Mock(side_effect=FileNotFoundError()))
def test_verified_command_exit_zero(tmp_path):
 fixture(tmp_path);runner=Mock(return_value=Mock(returncode=0))
 assert verify_cosign(tmp_path/'candidate.tar',tmp_path/'cosign.pub',tmp_path/'bundle.json',runner)
 assert '--key' in runner.call_args.args[0] and '--insecure-ignore-tlog' not in runner.call_args.args[0]
def test_signature_rejected(tmp_path):
 fixture(tmp_path)
 assert not verify_cosign(tmp_path/'candidate.tar',tmp_path/'cosign.pub',tmp_path/'bundle.json',Mock(return_value=Mock(returncode=1)))
def test_missing_archive(tmp_path):
 fixture(tmp_path);(tmp_path/'candidate.tar').unlink();runner=Mock()
 assert not verify_cosign(tmp_path/'candidate.tar',tmp_path/'cosign.pub',tmp_path/'bundle.json',runner)
 runner.assert_not_called()
