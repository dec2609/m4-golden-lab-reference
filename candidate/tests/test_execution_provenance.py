"""Producer boundary regression; subprocess doubles are UNIT_CONTRACT only."""
import json,sys,subprocess
from pathlib import Path
from unittest.mock import Mock,patch
import pytest
sys.path.append(str(Path(__file__).resolve().parents[1]/'scripts'))
import generate_sbom_m4 as generator
import source_security as scanner
import run_m4_controls as controls

@pytest.mark.parametrize('scanner_exit,payload,wrapper',[(7,None,2),(0,'{bad',2),(0,'{}',1)])
def test_sbom_preserves_actual_scanner_exit_and_invalid_raw(tmp_path,scanner_exit,payload,wrapper):
    image='localhost:5000/lab@sha256:'+'a'*64
    def execute(cmd):
        if cmd[0]=='docker':return subprocess.CompletedProcess(cmd,0,json.dumps([{'Id':'sha256:'+'b'*64,'RepoDigests':[image]}]),'')
        if cmd==['syft','version']:return subprocess.CompletedProcess(cmd,0,'Version: 1.54.1','')
        if payload is not None:Path(cmd[-1].split('=',1)[1]).write_text(payload)
        return subprocess.CompletedProcess(cmd,scanner_exit,'scanner stdout','scanner stderr')
    with patch.object(generator,'run',side_effect=execute),patch.object(sys,'argv',['generate_sbom_m4.py','--image',image,'--output-dir',str(tmp_path)]):
        assert generator.main()==wrapper
    execution=json.loads((tmp_path/'syft-execution.json').read_text())
    assert execution['raw_exit_code']==scanner_exit
    assert execution['command'][:2]==['syft',image]
    assert execution['stderr']=='scanner stderr'
    if payload is not None:assert (tmp_path/'order-app.spdx.json').read_text()==payload

def test_second_source_scope_error_preserves_prior_scope(tmp_path):
    calls=[]
    def execute(cmd,**kw):
        calls.append(cmd)
        if len(calls)==2:raise FileNotFoundError('scanner disappeared')
        Path(cmd[cmd.index('--report-path')+1]).write_text('[]')
        return subprocess.CompletedProcess(cmd,0,'history stdout','')
    with patch.object(scanner,'get_repo_context',return_value=('a'*40,False)),patch.object(scanner,'install_and_verify_gitleaks',return_value=True),patch.object(scanner.subprocess,'run',side_effect=execute):
        assert not scanner.run_scan(tmp_path)
    m=json.loads((tmp_path/'run_manifest.json').read_text())
    assert m['raw_exit_codes']==[0,None]
    assert len(m['commands'])==len(m['scope_executions'])==2
    assert m['scope_executions'][0]['stdout']=='history stdout'
    assert m['scope_executions'][1]['scope']=='worktree'

def test_missing_scanner_is_not_an_actual_exit_127():
    with patch.object(controls.subprocess,'run',side_effect=FileNotFoundError('missing')):
        assert controls.run(['trivy']).execution_started is False
