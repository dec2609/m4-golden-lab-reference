"""PROPOSED_REFERENCE_CHANGE: one local M4 CLI; actual entrypoints, no PASS substitution."""
import argparse,json,subprocess,sys
from pathlib import Path
from m4_result_adapter import checkout_snapshot,validate_control,read,require,runtime_allowed
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--phase',choices=['source','release'],default='release');p.add_argument('--image');p.add_argument('--source-git-context');p.add_argument('--public-key');p.add_argument('--private-key');p.add_argument('--trusted-key-sha256');p.add_argument('--stage',action='store_true');p.add_argument('--project');p.add_argument('--base-url',default='http://127.0.0.1:18081');p.add_argument('--previous-candidate');p.add_argument('--previous-status');a=p.parse_args()
    run=Path(a.run_dir).resolve();require(not run.is_relative_to(ROOT),'outputs must be outside checkout');require(not run.exists(),'unique new run required')
    dirty=subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],cwd=ROOT,text=True);require(not dirty.strip(),'clean source checkout required')
    run.mkdir(parents=True);summary={'contract_version':'m4-contract-1.0','run_id':run.name,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source_snapshot':checkout_snapshot(ROOT),'stages':{},'decision':'BLOCKED'}
    context={'contract':'reference-1','evidence_kind':'SOURCE_EXECUTION',**{k:summary[k] for k in ('run_id','source_commit','source_snapshot')}}
    source=run/'source-context.json';source.write_text(json.dumps(context,indent=2)+'\n',encoding='utf-8')
    def persist():(run/'run-summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    def execute(name,args):
        command=[sys.executable,'-B',*args];r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=600)
        (run/(name+'-stdout.log')).write_text(r.stdout,encoding='utf-8');(run/(name+'-stderr.log')).write_text(r.stderr,encoding='utf-8')
        summary['stages'][name]={'command':command,'exit_code':r.returncode};persist();return r.returncode
    # Failure of one source producer must not prevent independent evidence collection.
    execute('source-security',['scripts/source_security.py','--candidate',str(source),'--run-dir',str(run)])
    execute('dependency',['scripts/dependency_policy.py','--candidate',str(source),'--run-dir',str(run)])
    execute('unit',['scripts/m4_result_adapter.py','--unit','--candidate',str(source),'--run-dir',str(run)])
    approved=True
    for control in ('GITLEAKS','DEPENDENCY','UNIT_TEST'):
        try:
            assessment=validate_control(run,control,context);summary['stages'][control]={'evidence_valid':assessment.evidence_valid,'security_approved':assessment.security_approved,'policy_verdict':assessment.policy_verdict};approved &= assessment.security_approved
        except Exception as exc:summary['stages'][control]={'evidence_valid':False,'security_approved':False,'reason':str(exc)};approved=False
    if a.phase=='source':summary['decision']='SOURCE_CONTROLS_APPROVED' if approved else 'BLOCKED';persist();return 0 if approved else 1
    if not approved:summary['reason']='Source controls not approved; artifact/sign/deploy NOT_RUN';persist();return 1
    if not runtime_allowed():summary['reason']='BLOCKED_ENVIRONMENT: build/runtime resource guard';persist();return 2
    require(a.image,'release requires explicit local-registry image')
    args=['scripts/artifact_security.py','--run-dir',str(run),'--image',a.image]
    if a.public_key:args+=['--public-key',a.public_key]
    if a.source_git_context:args+=['--source-git-context',a.source_git_context]
    if execute('build-once',args):summary['reason']='actual build failed';persist();return 1
    candidate=run/'candidate.json'
    if a.private_key and a.trusted_key_sha256:
        execute('sign-verify',['scripts/artifact_security.py','--sign','--candidate',str(candidate),'--run-dir',str(run),'--private-key',a.private_key,'--trusted-key-sha256',a.trusted_key_sha256])
    else:summary['stages']['sign-verify']={'status':'NOT_RUN','reason':'operator-approved key and independent pin required'}
    # Current PR13 verifies the signed archive before scanning; signing is integrity, not release approval.
    if a.trusted_key_sha256:
        import os
        os.environ['M4_TRUSTED_PUBLIC_KEY_SHA256']=a.trusted_key_sha256
    execute('sbom-vulnerability',['scripts/run_m4_controls.py','--candidate',str(candidate),'--run-dir',str(run)])
    gate=['scripts/production_gate.py','--candidate',str(candidate),'--run-dir',str(run)]
    if a.trusted_key_sha256:gate+=['--trusted-key-sha256',a.trusted_key_sha256]
    if execute('gate',gate):summary['reason']='gate BLOCKED';persist();return 1
    summary['decision']='REPORTED_PRODUCTION_PASS'
    if a.stage:
        require(a.project and a.trusted_key_sha256,'isolated project and trust pin required')
        args=['--candidate',str(candidate),'--status',str(run/'release-status.json'),'--trusted-key-sha256',a.trusted_key_sha256,'--project',a.project,'--compose',str(ROOT/'docker-compose.staging.yml'),'--base-url',a.base_url]
        if execute('staging',['scripts/deploy_staging.py',*args]):
            if a.previous_candidate and a.previous_status:execute('rollback',['scripts/test_rollback.py',*args,'--approved-candidate',a.previous_candidate,'--approved-status',a.previous_status])
            else:summary['stages']['rollback']={'status':'NOT_RUN','reason':'previous approved candidate not provided'}
            summary['decision']='DEPLOYMENT_FAILED';persist();return 1
    persist();return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError,subprocess.SubprocessError) as exc:print('WORKFLOW_BLOCKED: '+str(exc),file=sys.stderr);raise SystemExit(2)
