"""FIXTURE contract vectors; not real scanners/signatures/runtime evidence."""
import os,json,copy,inspect
from pathlib import Path
import pytest

DOCS=Path(__file__).resolve().parents[2]/'docs/m4-contract'

def test_examples_match_published_schemas():
    import jsonschema
    for p in (DOCS/'examples').glob('*.result.json'):
        jsonschema.validate(json.loads(p.read_text()),json.loads((DOCS/'schemas/control-result.schema.json').read_text()))
    for p in (DOCS/'examples').glob('*.execution.json'):
        jsonschema.validate(json.loads(p.read_text()),json.loads((DOCS/'schemas/control-execution.schema.json').read_text()))

@pytest.fixture
def implementation():
    if not os.environ.get('M4_CONTRACT_IMPLEMENTATION'):
        pytest.skip('Set M4_CONTRACT_IMPLEMENTATION to owner checkout; schema-only pass is not conformance')
    import m4_result_adapter as adapter
    from _fixture import fixture,write
    return adapter,fixture,write

@pytest.mark.parametrize('verdict',['PASS','FAIL','ERROR'])
def test_validity_is_distinct_from_approval(tmp_path,implementation,verdict):
    a,f,w=implementation;c,key=f(tmp_path)
    r=a.read(tmp_path/'gitleaks-result.json');e=a.read(tmp_path/'gitleaks-execution.json')
    if verdict!='PASS':
        raw=1 if verdict=='FAIL' else 2
        r.update(policy_verdict=verdict,execution_status='SUCCESS' if verdict=='FAIL' else 'ERROR',raw_exit_code=raw)
        e['raw_exit_code']=raw
        p=tmp_path/'gitleaks-report.json';p.write_text('[{"RuleID":"FIXTURE"}]' if verdict=='FAIL' else '{}')
        r['report']['sha256']=e['report_sha256']=a.sha(p)
        w(tmp_path,'gitleaks-result.json',r);w(tmp_path,'gitleaks-execution.json',e)
    assessment=a.validate_control(tmp_path,'GITLEAKS',c)
    assert assessment.evidence_valid is True
    assert assessment.security_approved is (verdict=='PASS')
    with pytest.raises(TypeError):bool(assessment)

@pytest.mark.parametrize('mutation',['subject','tool','bool','source','run','hash','missing','empty','schema'])
def test_tampering_rejected(tmp_path,implementation,mutation):
    a,f,w=implementation;c,key=f(tmp_path);r=a.read(tmp_path/'gitleaks-result.json');e=a.read(tmp_path/'gitleaks-execution.json')
    if mutation=='subject':e['execution_subject']={'kind':'artifact','digest':'sha256:'+'f'*64}
    if mutation=='tool':e.pop('tool');r.pop('tool')
    if mutation=='bool':e['raw_exit_code']=r['raw_exit_code']=False
    if mutation=='source':e['source_commit']='f'*40
    if mutation=='run':e['run_id']='stale-run'
    if mutation=='hash':r['report']['sha256']='f'*64
    if mutation in ('empty','schema'):
        p=tmp_path/'gitleaks-report.json';p.write_text('' if mutation=='empty' else '{}');r['report']['sha256']=e['report_sha256']=a.sha(p)
    w(tmp_path,'gitleaks-result.json',r);w(tmp_path,'gitleaks-execution.json',e)
    if mutation=='missing':(tmp_path/'gitleaks-execution.json').unlink()
    with pytest.raises((ValueError,OSError)):a.validate_control(tmp_path,'GITLEAKS',c)

@pytest.mark.parametrize('control',['GITLEAKS','DEPENDENCY','UNIT_TEST'])
def test_source_only_subject(tmp_path,implementation,control):
    a,f,w=implementation;c,key=f(tmp_path)
    p=tmp_path/(control.lower().replace('_','-')+'-result.json');r=a.read(p)
    assert r['artifact_subject'] is None and r['execution_subject']['kind']=='source'
    assert a.validate_control(tmp_path,control,c).security_approved

def test_emitter_signature(implementation):
    a,_,_=implementation
    expected=['context','run_dir','control','report_path','raw_exit','verdict','tool','command','reason','wrapper_exit_code','policy_exit_code','repository_root','dependency_policy_path','expected_dependency_policy_sha256','scope','head_commit','dirty','shallow','raw_exit_codes','scanner_integrity']
    assert list(inspect.signature(a.emit_control).parameters)==expected
