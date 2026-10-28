"""Conformance regressions from fresh audit defects. All reports here are FIXTURES."""
import copy,json,subprocess,sys,importlib.util
from pathlib import Path
from unittest.mock import Mock
import pytest
from reference_fixture import fixture,write
import m4_result_adapter as adapter
from production_gate import evaluate_gate

def change(run,stem,record=None,execution=None,report=None):
    r=adapter.read(run/(stem+'-result.json'));e=adapter.read(run/(stem+'-execution.json'))
    if record:record(r)
    if execution:execution(e)
    if report is not None:
        p=run/(stem+'-report.json');p.write_text(json.dumps(report));r['report']['sha256']=e['report_sha256']=adapter.sha(p)
    write(run,stem+'-result.json',r);write(run,stem+'-execution.json',e)

@pytest.mark.parametrize('verdict',['PASS','FAIL','ERROR'])
def test_valid_record_is_not_approval(tmp_path,verdict):
    c,key=fixture(tmp_path)
    if verdict=='FAIL':
        change(tmp_path,'gitleaks',record=lambda r:r.update(policy_verdict='FAIL'),report=[{'RuleID':'FIXTURE'}])
    if verdict=='ERROR':
        change(tmp_path,'gitleaks',record=lambda r:r.update(policy_verdict='ERROR',execution_status='ERROR',raw_exit_code=None,report=None),execution=lambda e:e.update(raw_exit_code=None,execution_started=False,report_sha256=None))
    assessment=adapter.validate_control(tmp_path,'GITLEAKS',c)
    assert assessment.evidence_valid and assessment.security_approved is (verdict=='PASS')
    with pytest.raises(TypeError):bool(assessment)
    result,_=evaluate_gate(c,tmp_path,key,Mock(return_value=Mock(returncode=0)))
    assert result['PRODUCTION_GATE']==('PASS' if verdict=='PASS' else 'BLOCKED')

@pytest.mark.parametrize('mode',['wrong_execution_subject','missing_tool','boolean_exit','missing_execution','wrong_source','wrong_run','wrong_hash','empty_report','malformed_report'])
def test_current_audit_negatives(tmp_path,mode):
    c,key=fixture(tmp_path)
    r=adapter.read(tmp_path/'gitleaks-result.json');e=adapter.read(tmp_path/'gitleaks-execution.json')
    if mode=='wrong_execution_subject':e['execution_subject']={'kind':'source','source_commit':'f'*40,'source_snapshot':'f'*64}
    if mode=='missing_tool':r.pop('tool');e.pop('tool')
    if mode=='boolean_exit':r['raw_exit_code']=e['raw_exit_code']=False
    if mode=='wrong_source':r['source_commit']='f'*40
    if mode=='wrong_run':e['run_id']='old-run'
    if mode=='wrong_hash':r['report']['sha256']='f'*64
    if mode in ('empty_report','malformed_report'):
        p=tmp_path/'gitleaks-report.json';p.write_text('' if mode=='empty_report' else '{bad');r['report']['sha256']=e['report_sha256']=adapter.sha(p)
    write(tmp_path,'gitleaks-result.json',r);write(tmp_path,'gitleaks-execution.json',e)
    if mode=='missing_execution':(tmp_path/'gitleaks-execution.json').unlink()
    with pytest.raises((ValueError,OSError)):adapter.validate_control(tmp_path,'GITLEAKS',c)
    assert evaluate_gate(c,tmp_path,key,Mock(return_value=Mock(returncode=0)))[0]['PRODUCTION_GATE']=='BLOCKED'

@pytest.mark.parametrize('name',['fixture-run','previous-run','real-run'])
def test_fixture_name_never_selects_weaker_validation(tmp_path,name):
    run=tmp_path/name;run.mkdir();c,key=fixture(run)
    change(run,'sbom',execution=lambda e:e.update(execution_subject={'kind':'artifact','digest':'sha256:'+'f'*64}))
    with pytest.raises(ValueError):adapter.validate_control(run,'SBOM',c)

@pytest.mark.parametrize('control',['GITLEAKS','DEPENDENCY','UNIT_TEST'])
def test_source_only_controls_have_no_fabricated_artifact(tmp_path,control):
    c,key=fixture(tmp_path);r=adapter.read(tmp_path/(control.lower().replace('_','-')+'-result.json'))
    assert r['artifact_subject'] is None and r['execution_subject']['kind']=='source'
    assert r['execution_subject']['source_commit']==c['source_commit']

def test_actual_source_cli_to_actual_emitter(tmp_path,monkeypatch):
    spec=importlib.util.spec_from_file_location('helpers',Path(__file__).with_name('test_m4_candidate_contract.py'));h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    repo=h.make_checkout(tmp_path);run=tmp_path/'cli-run';run.mkdir()
    c={'contract':'reference-1','evidence_kind':'SOURCE_EXECUTION','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),'source_snapshot':adapter.checkout_snapshot(repo),'run_id':run.name}
    context=write(run,'source-context.json',c)
    import source_security as source
    monkeypatch.setattr(source,'ROOT',repo);monkeypatch.setattr(source,'ACTUAL_VERSION','8.18.4');monkeypatch.setattr(source,'install_and_verify_gitleaks',lambda:True)
    def scanner(cmd,**kw):
        Path(cmd[cmd.index('--report-path')+1]).write_text('[]');return subprocess.CompletedProcess(cmd,0,'FIXTURE SCANNER DOUBLE','')
    monkeypatch.setattr(source,'execute_scanner',scanner);monkeypatch.setattr(sys,'argv',['source_security.py','--candidate',str(context),'--run-dir',str(run)])
    assert source.main()==0
    assert adapter.validate_control(run,'GITLEAKS',c,repository_root=repo).security_approved

def test_workflow_calls_existing_cli_and_no_m3_or_literal_pass():
    repo=Path(__file__).resolve().parents[1];workflow=(repo/'.github/workflows/verify.yml').read_text()
    assert 'run_m4_workflow.py --run-dir' in workflow and 'bang-chung/m3' not in workflow and 'status: PASS' not in workflow
    p=subprocess.run([sys.executable,'-B',str(repo/'scripts/run_m4_controls.py'),'--help'],capture_output=True,text=True)
    assert p.returncode==0 and '--run-dir' in p.stdout and '--candidate' in p.stdout


def test_candidate_runner_is_importable_and_make_uses_m4():
    import scripts.m4_candidate_controls
    make=(Path(__file__).resolve().parents[1]/'Makefile').read_text(encoding='utf-8')
    assert 'run_m4_workflow.py --phase source' in make
    assert 'down -v' not in make and 'python tests/test_production_gate.py' not in make


def test_oci_archive_index_and_platform_binding(tmp_path):
    import tarfile,io,hashlib
    c,key=fixture(tmp_path)
    def hashed(data):return 'sha256:'+hashlib.sha256(data).hexdigest()
    config=json.dumps({'config':{'Labels':{'org.opencontainers.image.revision':c['source_commit'],'orderflow.source_snapshot':c['source_snapshot']}}}).encode()
    layer=b'EXPLICIT OCI CONTRACT FIXTURE';conf=hashed(config);ld=hashed(layer)
    manifest=json.dumps({'schemaVersion':2,'mediaType':'application/vnd.oci.image.manifest.v1+json','config':{'digest':conf},'layers':[{'digest':ld}]}).encode();pd=hashed(manifest)
    index=json.dumps({'schemaVersion':2,'manifests':[{'digest':pd}]}).encode();ix=hashed(index)
    with tarfile.open(tmp_path/'oci.tar','w') as t:
        for name,b in [('index.json',json.dumps({'manifests':[{'digest':ix}]}).encode()),*[( 'blobs/sha256/'+hashed(b)[7:],b) for b in (config,layer,manifest,index)]]:
            info=tarfile.TarInfo(name);info.size=len(b);t.addfile(info,io.BytesIO(b))
    (tmp_path/'registry-index.json').write_bytes(index);(tmp_path/'registry-manifest.json').write_bytes(manifest)
    c.update(archive_path='oci.tar',archive_sha256=adapter.sha(tmp_path/'oci.tar'),config_digest=conf,manifest_digest=ix,platform_manifest_digest=pd)
    assert adapter.verify_archive(tmp_path,c)==tmp_path/'oci.tar'
    assert adapter.verify_registry(tmp_path,c)
    c['platform_manifest_digest']='sha256:'+'f'*64
    with pytest.raises(ValueError):adapter.verify_archive(tmp_path,c)


@pytest.mark.parametrize('field',['policy_sha256','manifest_sha256'])
def test_dependency_input_hash_is_required(tmp_path,field):
    c,key=fixture(tmp_path)
    report=adapter.read(tmp_path/'dependency-report.json');report.pop(field)
    change(tmp_path,'dependency',report=report)
    with pytest.raises(ValueError):adapter.validate_control(tmp_path,'DEPENDENCY',c)

@pytest.mark.parametrize('field',['wrapper_exit_code','policy_exit_code'])
def test_required_null_fields_cannot_be_omitted(tmp_path,field):
    c,key=fixture(tmp_path);r=adapter.read(tmp_path/'gitleaks-result.json');r.pop(field);write(tmp_path,'gitleaks-result.json',r)
    with pytest.raises(ValueError):adapter.validate_control(tmp_path,'GITLEAKS',c)
