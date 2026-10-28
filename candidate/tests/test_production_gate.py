"""Migrated from removed six-control evaluate_gate API; original preserved in lab-evidence."""
from reference_fixture import fixture
from production_gate import evaluate_gate
from unittest.mock import Mock

def test_m4_eight_controls_and_missing_evidence(tmp_path):
 c,key=fixture(tmp_path)
 (tmp_path/'sbom-result.json').unlink()
 result,reasons=evaluate_gate(c,tmp_path,key,Mock(return_value=Mock(returncode=0)))
 assert len(result['controls'])==8 and result['controls']['SBOM_STATUS']=='FAIL'
 assert result['PRODUCTION_GATE']=='BLOCKED' and 'SBOM' in reasons
