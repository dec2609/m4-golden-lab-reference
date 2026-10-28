import copy, json, subprocess
from pathlib import Path
from unittest.mock import Mock
import pytest
from reference_fixture import fixture,write
from m4_result_adapter import read,sha,validate_control
from production_gate import evaluate_gate,clean_status
from m4_result_adapter import bind_result

def test_positive_producer_consumer_fixture(tmp_path):
    c,key=fixture(tmp_path);run=Mock(return_value=subprocess.CompletedProcess([],0,'FIXTURE',''))
    result,reasons=evaluate_gate(c,tmp_path,key,run)
    assert result['PRODUCTION_GATE']=='PASS' and not reasons
    assert result['deployment']['DEPLOYMENT_GATE']=='NOT_RUN'
    assert len(result['controls'])==8 and run.call_args.args[0][1]=='verify-blob'

@pytest.mark.parametrize('value',['NOT_PASS','BYPASS','UNKNOWN','PASS=FAIL','control=PASS','pass',' PASS','',None,'INFRA_BLOCKED','NOT_RUN'])
def test_exact_status_rejects_ambiguous(value):assert clean_status(value)=='FAIL'

@pytest.mark.parametrize('name',['gitleaks','dependency','unit-test','sbom','vulnerability'])
@pytest.mark.parametrize('mode',['missing','empty','malformed','wrong_hash','wrong_run','wrong_source','wrong_snapshot','wrong_subject','exit2','NOT_RUN','BYPASS'])
def test_negative_record_matrix(tmp_path,name,mode):
    c,key=fixture(tmp_path);p=tmp_path/(name+'-result.json');r=read(p)
    if mode=='missing':p.unlink()
    elif mode=='empty':p.write_text('')
    elif mode=='malformed':p.write_text('{')
    else:
        if mode=='wrong_hash':r['report']['sha256']='f'*64
        elif mode=='wrong_run':r['run_id']='stale'
        elif mode=='wrong_source':r['source_commit']='c'*40
        elif mode=='wrong_snapshot':r['source_snapshot']='c'*64
        elif mode=='wrong_subject':r['artifact_subject']='sha256:'+'c'*64
        elif mode=='exit2':r['raw_exit_code']=2
        elif mode=='NOT_RUN':r['execution_status']='NOT_RUN'
        elif mode=='BYPASS':r['policy_verdict']='BYPASS'
        write(tmp_path,p.name,r)
    result,_=evaluate_gate(c,tmp_path,key,Mock(return_value=Mock(returncode=0)))
    assert result['PRODUCTION_GATE']=='BLOCKED'
    assert result['controls'][name.upper().replace('-','_')+'_STATUS']=='FAIL'

@pytest.mark.parametrize('report',[{},[],{'Results':[]},{'Results':{}},{'SchemaVersion':2,'ArtifactName':'wrong','Results':[]},'malformed'])
def test_empty_invalid_trivy_cannot_pass_even_rehashed(tmp_path,report):
    c,key=fixture(tmp_path);p=write(tmp_path,'vulnerability-report.json',report);r=read(tmp_path/'vulnerability-result.json');e=read(tmp_path/'vulnerability-execution.json');r['report']['sha256']=sha(p);e['report_sha256']=sha(p);write(tmp_path,'vulnerability-result.json',r);write(tmp_path,'vulnerability-execution.json',e)
    assert evaluate_gate(c,tmp_path,key,Mock(return_value=Mock(returncode=0)))[0]['PRODUCTION_GATE']=='BLOCKED'

@pytest.mark.parametrize('kind',['CRITICAL','wrong_image','wrong_digest','invalid_vuln_type','invalid_severity'])
def test_trivy_policy_and_subject(tmp_path,kind):
    c,key=fixture(tmp_path);r=read(tmp_path/'vulnerability-report.json')
    if kind=='CRITICAL':r['Results'][0]['Vulnerabilities']=[{'VulnerabilityID':'FIXTURE-CVE','Severity':'CRITICAL'}]
    elif kind=='wrong_image':r['ArtifactName']='other'
    elif kind=='wrong_digest':r['Metadata']['RepoDigests']=['wrong@sha256:'+'f'*64]
    elif kind=='invalid_vuln_type':r['Results'][0]['Vulnerabilities']={}
    else:r['Results'][0]['Vulnerabilities']=[{'VulnerabilityID':'FIXTURE-CVE','Severity':'BYPASS'}]
    p=write(tmp_path,'vulnerability-report.json',r)
    for name in ['vulnerability-result.json','vulnerability-execution.json']:
        r=read(tmp_path/name)
        if 'report' in r:r['report']['sha256']=sha(p)
        else:r['report_sha256']=sha(p)
        write(tmp_path,name,r)
    assert evaluate_gate(c,tmp_path,key,Mock(return_value=Mock(returncode=0)))[0]['PRODUCTION_GATE']=='BLOCKED'

@pytest.mark.parametrize('mode',['archive_tamper','registry_tamper','wrong_key','cosign_exit1','cosign_missing','no_execution','execution_exit2','path_escape','gitleaks_finding_exit0','gitleaks_dirty','gitleaks_scope','gitleaks_shallow','sbom_empty'])
def test_other_attack_cases(tmp_path,mode):
    c,key=fixture(tmp_path);run=Mock(return_value=Mock(returncode=0))
    if mode=='archive_tamper':(tmp_path/'candidate.tar').write_bytes(b'tampered')
    elif mode=='registry_tamper':(tmp_path/'registry-manifest.json').write_text('{}')
    elif mode=='wrong_key':key='f'*64
    elif mode=='cosign_exit1':run.return_value.returncode=1
    elif mode=='cosign_missing':run.side_effect=FileNotFoundError('cosign')
    elif mode=='no_execution':(tmp_path/'gitleaks-execution.json').unlink()
    elif mode=='execution_exit2':r=read(tmp_path/'gitleaks-execution.json');r['raw_exit_code']=2;write(tmp_path,'gitleaks-execution.json',r)
    elif mode=='path_escape':r=read(tmp_path/'gitleaks-result.json');r['report']['path']='../outside.json';write(tmp_path,'gitleaks-result.json',r)
    elif mode.startswith('gitleaks_') and mode!='gitleaks_finding_exit0':
        r=read(tmp_path/'gitleaks-execution.json');r['source_context'][{'gitleaks_dirty':'dirty','gitleaks_scope':'scope','gitleaks_shallow':'shallow'}[mode]]={'gitleaks_dirty':True,'gitleaks_scope':'HISTORY_ONLY','gitleaks_shallow':True}[mode];write(tmp_path,'gitleaks-execution.json',r)
    else:
        stem='sbom' if mode=='sbom_empty' else 'gitleaks';p=write(tmp_path,stem+'-report.json',{} if stem=='sbom' else [{'RuleID':'fixture'}]);r=read(tmp_path/(stem+'-result.json'));e=read(tmp_path/(stem+'-execution.json'));r['report']['sha256']=sha(p);e['report_sha256']=sha(p);write(tmp_path,stem+'-result.json',r);write(tmp_path,stem+'-execution.json',e)
    assert evaluate_gate(c,tmp_path,key,run)[0]['PRODUCTION_GATE']=='BLOCKED'

def test_handoff_consumes_tram_record_without_identity_rewrite(tmp_path):
    src=tmp_path/'source';src.mkdir();c,key=fixture(src);r=read(src/'sbom-result.json');e=read(src/'sbom-execution.json');out=tmp_path/'target'/c['run_id']
    bind_result(r,e,c,src,out);assert validate_control(out,'SBOM',c).security_approved
    with pytest.raises(ValueError,match='overwrite'):bind_result(r,e,c,src,out)
    r['run_id']='stale'
    with pytest.raises(ValueError,match='run_id'):bind_result(r,e,c,src,out)
