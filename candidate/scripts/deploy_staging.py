"""Explicit isolated deployment/rollback. No volume deletion, shared names or synthetic success."""
import json, os, re, subprocess, time, urllib.error, urllib.request
from pathlib import Path
from m4_result_adapter import candidate, require
from production_gate import validate_schema

def check_endpoint(path,base_url='http://127.0.0.1:18081'):
    try:
        with urllib.request.urlopen(base_url+path,timeout=3) as response:
            code=response.status
            if code!=200:return False,code
            body=json.loads(response.read().decode('utf-8'))
            if path=='/ready':ok=isinstance(body,dict) and body.get('status')=='ready' and body.get('database')=='connected' and not body.get('error')
            elif path=='/health':ok=isinstance(body,dict) and body.get('status')=='ok'
            elif path=='/orders':ok=isinstance(body,dict) and isinstance(body.get('orders'),list)
            else:ok=False
            return bool(ok),code
    except urllib.error.HTTPError as exc:return False,exc.code
    except (OSError,ValueError,UnicodeError):return False,0

def validate_release(status,c):
    validate_schema(status)
    require(status['PRODUCTION_GATE']=='PASS' and all(v=='PASS' for v in status['controls'].values()),'release gate not PASS')
    require(status['source_commit']==c['source_commit'] and status['artifact_sha256']==c['archive_sha256'] and status['image_digest']==c['manifest_digest'] and status['registry']['image_reference']==c['image_reference'] and status['registry']['image_digest']==c['manifest_digest'],'release/candidate mismatch')

def operate(status_path,c,project,compose_file,base_url,runner=subprocess.run,probe=check_endpoint,rollback_to=None,approved_status=None,attempts=10,delay=1):
    candidate(c)
    require(re.fullmatch('m4-golden-[a-z0-9-]+',project) is not None,'isolated project required')
    require(re.fullmatch(r'http://127\.0\.0\.1:[0-9]+',base_url) is not None,'loopback lab endpoint required')
    path=Path(status_path);status=json.loads(path.read_text(encoding='utf-8'));validate_release(status,c)
    is_rollback=rollback_to is not None
    target=c
    if is_rollback:
        require(status['deployment']['DEPLOYMENT_GATE']=='FAIL','rollback requires a failed deployment')
        target=candidate(rollback_to);require(approved_status is not None,'missing previous approval');validate_release(approved_status,target)
        require(all(target[k]!=c[k] for k in ('run_id','manifest_digest','config_digest')),'rollback requires a distinct previous run and immutable image')
    events=[];ok=False
    try:
        env=dict(os.environ,ORDER_APP_IMAGE=target['image_reference'])
        prefix=['docker','compose','--project-name',project,'-f',str(compose_file)]
        p=runner(prefix+['up','-d','--no-build','order-app'],env=env,capture_output=True,text=True,timeout=90)
        events.append({'step':'compose-up','exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
        require(p.returncode==0,'Compose command failed')
        p=runner(prefix+['ps','-q','order-app'],env=env,capture_output=True,text=True,timeout=15)
        require(p.returncode==0 and re.fullmatch('[0-9a-f]{12,64}',p.stdout.strip()) is not None,'container identity unavailable')
        p=runner(['docker','inspect','--format','{{.Image}}',p.stdout.strip()],capture_output=True,text=True,timeout=15)
        require(p.returncode==0 and p.stdout.strip()==target['config_digest'],'restored/deployed config digest mismatch')
        ready=health=api=False
        for attempt in range(attempts):
            ready=probe('/ready',base_url)[0];health=probe('/health',base_url)[0];api=probe('/orders',base_url)[0]
            if ready and health and api:break
            if attempt+1<attempts:time.sleep(delay)
        events.append({'step':'probes','readiness':ready,'health':health,'orders':api,'config_digest':p.stdout.strip()})
        ok=ready and health and api
    except (ValueError,OSError,subprocess.SubprocessError) as exc:events.append({'error':str(exc)})
    if is_rollback:status['deployment']['ROLLBACK_STATUS']='PASS' if ok else 'FAIL'
    else:status['deployment']={'READINESS_STATUS':'PASS' if ok else 'FAIL','API_STATUS':'PASS' if ok else 'FAIL','DEPLOYMENT_GATE':'PASS' if ok else 'FAIL','ROLLBACK_STATUS':'NOT_REQUIRED'}
    # One release document and lifecycle log, bound to the failed/current run even when restoring a previous candidate.
    path.write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8')
    event={'run_id':c['run_id'],'source_commit':c['source_commit'],'candidate_digest':c['manifest_digest'],'target_digest':target['manifest_digest'],'operation':'rollback' if is_rollback else 'deployment','status':'PASS' if ok else 'FAIL','events':events}
    with path.with_name('lifecycle.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event)+'\n')
    return 0 if ok else 1

import argparse,json
from pathlib import Path
from production_gate import evaluate_gate
from m4_result_adapter import load_context
from m4_result_adapter import read,require
def main(rollback=False):
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--status',required=True);p.add_argument('--trusted-key-sha256',required=True);p.add_argument('--project',required=True);p.add_argument('--compose',required=True);p.add_argument('--base-url',required=True);p.add_argument('--approved-candidate');p.add_argument('--approved-status');a=p.parse_args()
    if rollback and (not a.approved_candidate or not a.approved_status):p.error('rollback requires previous candidate and approved status')
    try:
        from m4_result_adapter import runtime_allowed
        require(runtime_allowed(),'BLOCKED_ENVIRONMENT: insufficient resources for deployment')
        c=load_context(a.candidate);root=Path(a.status).resolve().parent
        require(root.name==c['run_id'],'deployment run mismatch')
        actual,_=evaluate_gate(c,root,a.trusted_key_sha256)
        require(c.get('evidence_kind')=='BUILD_EXECUTION' and actual['PRODUCTION_GATE']=='PASS','actual gate evidence does not approve deployment')
        old=read(a.approved_candidate) if a.approved_candidate else None
        previous=read(a.approved_status) if a.approved_status else None
        if old is not None:
            old_gate,_=evaluate_gate(old,Path(a.approved_status).resolve().parent,a.trusted_key_sha256)
            require(old.get('evidence_kind')=='BUILD_EXECUTION' and old_gate['PRODUCTION_GATE']=='PASS','previous artifact has no verified gate evidence')
        return operate(a.status,c,a.project,a.compose,a.base_url,rollback_to=old,approved_status=previous)
    except Exception as exc:print('DEPLOYMENT BLOCKED: '+str(exc));return 2
if __name__=='__main__':raise SystemExit(main())
