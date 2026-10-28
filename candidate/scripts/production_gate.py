"""M4 reference gate. Explicit inputs only; no historical status/env fallback."""
import argparse, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from m4_result_adapter import CONTROLS, candidate, child, hexid, read, require, sha, validate_control, verify_archive, verify_registry, checkout_snapshot
ROOT=Path(__file__).resolve().parents[1]
SCHEMA_V2_FILE=ROOT/'cau-hinh/release-status.schema.v2.json'
REQUIRED_CONTROLS=[c+'_STATUS' for c in CONTROLS]
def clean_status(value): return 'PASS' if value=='PASS' else 'FAIL'
def validate_schema(data):
    import jsonschema
    jsonschema.validate(data,read(SCHEMA_V2_FILE))
def verify_cosign(archive,key,bundle,runner=subprocess.run):
    try:
        if not all(Path(p).is_file() and Path(p).stat().st_size for p in (archive,key,bundle)):return False
        result=runner(['cosign','verify-blob','--key',str(key),'--bundle',str(bundle),str(archive)],capture_output=True,text=True,timeout=45)
        return result.returncode==0
    except (OSError,subprocess.SubprocessError): return False
def evaluate_gate(context,run_dir,trusted_key_sha256,runner=subprocess.run):
    """Expected context is supplied by a trusted build orchestrator. Injected runner is a unit double only."""
    c=candidate(context);states={name+'_STATUS':'FAIL' for name in CONTROLS};reasons={}
    def check(name,fn):
        try: require(fn() is True,name+' validation failed');states[name+'_STATUS']='PASS'
        except Exception as exc: reasons[name]=str(exc)
    for name in ('GITLEAKS','DEPENDENCY','UNIT_TEST','SBOM','VULNERABILITY'):
        check(name,lambda name=name:validate_control(run_dir,name,c).security_approved)
    def archive_check(): verify_archive(run_dir,c);return True
    check('DIGEST',archive_check)
    check('REGISTRY',lambda:verify_registry(run_dir,c))
    def cosign_check():
        require(states['DIGEST_STATUS']=='PASS','unsigned/unmeasured archive')
        key=child(run_dir,c.get('public_key_path'));bundle=child(run_dir,c.get('bundle_path'))
        require(hexid(trusted_key_sha256,64) and sha(key)==trusted_key_sha256,'unpinned/untrusted key')
        return verify_cosign(child(run_dir,c['archive_path']),key,bundle,runner)
    check('COSIGN',cosign_check)
    output={'schema_version':2,'source_commit':c['source_commit'],'artifact_sha256':c['archive_sha256'],'image_digest':c['manifest_digest'],'registry':{'image_reference':c['image_reference'],'image_digest':c['manifest_digest']},'controls':states,'PRODUCTION_GATE':'PASS' if all(v=='PASS' for v in states.values()) else 'BLOCKED','deployment':{'READINESS_STATUS':'NOT_RUN','API_STATUS':'NOT_RUN','DEPLOYMENT_GATE':'NOT_RUN','ROLLBACK_STATUS':'NOT_REQUIRED'}}
    validate_schema(output)
    return output,reasons
def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--run-dir',required=True);p.add_argument('--trusted-key-sha256');p.add_argument('--block-reason');a=p.parse_args()
    run_dir=Path(a.run_dir).resolve();output=run_dir/'release-status.json'
    output.unlink(missing_ok=True)
    try:
        c=read(a.candidate)
        require(run_dir.name==c.get('run_id'),'run directory identity mismatch')
        actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        require(actual==c.get('source_commit'),'candidate not built from this checkout')
        require(checkout_snapshot(ROOT)==c.get('source_snapshot'),'checkout source snapshot mismatch')
        dirty=subprocess.check_output(['git','status','--porcelain','--untracked-files=all','--','scripts','tests','ma-nguon/order-app','ma-nguon/database','.github','cau-hinh'],cwd=ROOT,text=True)
        require(not dirty.strip(),'build source checkout is dirty')
        result,reasons=evaluate_gate(c,run_dir,a.trusted_key_sha256)
        if c.get('evidence_kind')!='BUILD_EXECUTION':
            result['PRODUCTION_GATE']='BLOCKED';reasons['CANDIDATE']='No current build execution context; diagnostic/fixture cannot approve release'
        if a.block_reason:
            result['PRODUCTION_GATE']='BLOCKED';reasons['ORCHESTRATION']=a.block_reason
        # PROVISIONAL_FOR_LAB: run binding is consistency metadata, not authentication.
        result['provenance']={k:c[k] for k in ('run_id','source_commit','source_snapshot')}
        result['provenance'].update(artifact_sha256=c['archive_sha256'],image_digest=c['manifest_digest'],generated_at=datetime.now(timezone.utc).isoformat().replace('+00:00','Z'))
        output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        (run_dir/'gate-reasons.json').write_text(json.dumps(reasons,indent=2)+'\n',encoding='utf-8')
        print(result['PRODUCTION_GATE']);return 0 if result['PRODUCTION_GATE']=='PASS' else 1
    except Exception as exc:
        print('BLOCKED: '+str(exc),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
