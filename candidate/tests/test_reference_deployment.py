import json,subprocess
from unittest.mock import Mock,patch
import pytest
from reference_fixture import fixture,write
from production_gate import evaluate_gate
from deploy_staging import check_endpoint,operate

@pytest.mark.parametrize('code,body,expected',[(200,{'status':'ready','database':'connected'},True),(200,{'status':'ok'},False),(200,{'status':'ready','database':'disconnected'},False),(200,{'status':'ready','database':'connected','error':'outage'},False),(404,{},False),(503,{'status':'unready'},False),(200,'HTML',False)])
def test_readiness_contract(code,body,expected):
    response=Mock(status=code);response.read.return_value=json.dumps(body).encode();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
    with patch('deploy_staging.urllib.request.urlopen',return_value=response):assert check_endpoint('/ready')[0] is expected

def setup_run(tmp_path):
    c,key=fixture(tmp_path);status,_=evaluate_gate(c,tmp_path,key,Mock(return_value=Mock(returncode=0)));path=write(tmp_path,'release-status.json',status);return c,status,path
@pytest.mark.parametrize('rollback',[False,True])
@pytest.mark.parametrize('mode',['command_failure','wrong_digest','ready_false','positive'])
def test_command_and_immutable_identity(tmp_path,rollback,mode):
    c,status,path=setup_run(tmp_path)
    target=c;approval=None
    if rollback:
        previous=tmp_path/'previous';previous.mkdir();target,key=fixture(previous,revision='c',snapshot='d',run_id='previous-run')
        approval,_=evaluate_gate(target,previous,key,Mock(return_value=Mock(returncode=0)))
    if rollback:status['deployment']={'READINESS_STATUS':'FAIL','API_STATUS':'FAIL','DEPLOYMENT_GATE':'FAIL','ROLLBACK_STATUS':'NOT_REQUIRED'};write(tmp_path,path.name,status)
    def run(cmd,**kwargs):
        if mode=='command_failure':return Mock(returncode=1,stdout='',stderr='INJECTED COMMAND FAILURE')
        if 'up' in cmd:return Mock(returncode=0,stdout='',stderr='')
        if 'ps' in cmd:return Mock(returncode=0,stdout='c'*64,stderr='')
        return Mock(returncode=0,stdout='sha256:'+'f'*64 if mode=='wrong_digest' else target['config_digest'],stderr='')
    probe=Mock(return_value=(mode!='ready_false',200))
    ret=operate(path,c,'m4-golden-fixture','fixture-compose.yml','http://127.0.0.1:18081',runner=run,probe=probe,rollback_to=target if rollback else None,approved_status=approval,attempts=1,delay=0)
    assert ret==(0 if mode=='positive' else 1)
    actual=json.loads(path.read_text());field='ROLLBACK_STATUS' if rollback else 'DEPLOYMENT_GATE'
    assert actual['deployment'][field]==('PASS' if mode=='positive' else 'FAIL')
    if mode=='command_failure':probe.assert_not_called()
    if rollback:assert actual['deployment']['DEPLOYMENT_GATE']=='FAIL'
    events=json.loads(path.with_name('lifecycle.jsonl').read_text());assert events['run_id']==c['run_id'] and events['candidate_digest']==c['manifest_digest']
def test_rollback_refuses_unapproved_previous_candidate(tmp_path):
    c,status,path=setup_run(tmp_path);status['deployment']={'READINESS_STATUS':'FAIL','API_STATUS':'FAIL','DEPLOYMENT_GATE':'FAIL','ROLLBACK_STATUS':'NOT_REQUIRED'};write(tmp_path,path.name,status)
    with pytest.raises(ValueError,match='approval'):operate(path,c,'m4-golden-fixture','x','http://127.0.0.1:18081',rollback_to=c)

def test_rollback_restores_distinct_previous_approved_artifact(tmp_path):
    current=tmp_path/'current';current.mkdir();c,status,path=setup_run(current)
    previous=tmp_path/'previous';previous.mkdir();old,key=fixture(previous,revision='c',snapshot='d',run_id='previous-run')
    approval,_=evaluate_gate(old,previous,key,Mock(return_value=Mock(returncode=0)))
    status['deployment']={'READINESS_STATUS':'FAIL','API_STATUS':'FAIL','DEPLOYMENT_GATE':'FAIL','ROLLBACK_STATUS':'NOT_REQUIRED'};write(current,path.name,status)
    calls=[]
    def run(cmd,**kwargs):
        calls.append((cmd,kwargs))
        return Mock(returncode=0,stderr='',stdout='e'*64 if 'ps' in cmd else old['config_digest'] if 'inspect' in cmd else '')
    assert c['config_digest']!=old['config_digest']
    assert operate(path,c,'m4-golden-fixture','fixture-compose.yml','http://127.0.0.1:18081',runner=run,probe=Mock(return_value=(True,200)),rollback_to=old,approved_status=approval,attempts=1,delay=0)==0
    assert calls[0][1]['env']['ORDER_APP_IMAGE']==old['image_reference']
    actual=json.loads(path.read_text());assert actual['image_digest']==c['manifest_digest'] and actual['deployment']['DEPLOYMENT_GATE']=='FAIL' and actual['deployment']['ROLLBACK_STATUS']=='PASS'

@pytest.mark.parametrize('reuse',['run_id','manifest_digest','config_digest'])
def test_rollback_rejects_current_identity_before_any_runtime_command(tmp_path,reuse):
    current=tmp_path/'current';current.mkdir();c,status,path=setup_run(current)
    previous=tmp_path/'previous';previous.mkdir();old,key=fixture(previous,revision='c',snapshot='d',run_id='previous-run')
    approval,_=evaluate_gate(old,previous,key,Mock(return_value=Mock(returncode=0)))
    status['deployment']={'READINESS_STATUS':'FAIL','API_STATUS':'FAIL','DEPLOYMENT_GATE':'FAIL','ROLLBACK_STATUS':'NOT_REQUIRED'};write(current,path.name,status)
    old[reuse]=c[reuse]
    if reuse=='manifest_digest':
        old['image_reference']=old['image_reference'].split('@')[0]+'@'+old['manifest_digest'];old['artifact_subject']=old['manifest_digest']
        approval['image_digest']=old['manifest_digest'];approval['registry']['image_digest']=old['manifest_digest'];approval['registry']['image_reference']=old['image_reference']
    before=path.read_bytes();runner=Mock(side_effect=AssertionError('runtime command reached with current candidate identity'));probe=Mock()
    with pytest.raises(ValueError,match='distinct previous'):
        operate(path,c,'m4-golden-fixture','fixture-compose.yml','http://127.0.0.1:18081',runner=runner,probe=probe,rollback_to=old,approved_status=approval)
    runner.assert_not_called();probe.assert_not_called()
    assert path.read_bytes()==before and not path.with_name('lifecycle.jsonl').exists()
