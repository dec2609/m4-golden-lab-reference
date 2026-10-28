"""M4 build-once and explicit signing entrypoint. No archive reuse, default password or literal PASS."""
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path
from m4_result_adapter import read,require,sha,checkout_snapshot,verify_archive,verify_registry
from m4_result_adapter import load_context
from production_gate import verify_cosign
from verify_registry import capture_manifest
ROOT=Path(__file__).resolve().parents[1]
def execute(command,root):
    p=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=300)
    with (root/'artifact-execution.jsonl').open('ab') as f:f.write((json.dumps({'command':command,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})+'\n').encode())
    require(p.returncode==0,'artifact command failed: '+command[0])
    return p.stdout
def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--image');p.add_argument('--source-git-context');p.add_argument('--public-key');p.add_argument('--private-key');p.add_argument('--trusted-key-sha256');p.add_argument('--candidate');p.add_argument('--sign',action='store_true');a=p.parse_args()
    root=Path(a.run_dir).resolve()
    try:
        if a.sign:
            c=load_context(a.candidate);require(root.name==c['run_id'],'sign run mismatch')
            require(a.private_key and Path(a.private_key).is_file(),'missing signing key')
            key=root/c['public_key_path'];require(sha(key)==a.trusted_key_sha256,'unapproved signing public key')
            require(not (root/c['bundle_path']).exists(),'signing refuses old bundle')
            archive=verify_archive(root,c);verify_registry(root,c)
            execute(['cosign','sign-blob','--yes','--key',str(Path(a.private_key).resolve()),'--bundle',str(root/c['bundle_path']),str(archive)],root)
            require(verify_cosign(archive,key,root/c['bundle_path']),'actual Cosign verification failed')
            return 0
        require(a.image,'build requires an explicit image');require(not a.public_key or Path(a.public_key).is_file(),'provided public key missing')
        from m4_result_adapter import runtime_allowed
        require(runtime_allowed(),'BLOCKED_ENVIRONMENT: insufficient measured resources for build')
        require(not root.is_relative_to(ROOT),'build outputs must be outside scanned source checkout')
        require(not (root/'candidate.json').exists() and not (root/'candidate.tar').exists(),'build refuses artifact reuse')
        if root.exists():
            source=load_context(root/'source-context.json');require(source['run_id']==root.name,'build/source run mismatch')
        repository,tag=a.image.rsplit(':',1);require('/' in repository and tag,'explicit repository:run-tag required')
        host=repository.split('/')[0];require(host.split(':')[0] in ('localhost','127.0.0.1'),'only isolated local registry supported')
        root.mkdir(parents=True,exist_ok=True)
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();snapshot=checkout_snapshot(ROOT)
        dirty=subprocess.check_output(['git','status','--porcelain','--','scripts','tests','ma-nguon/order-app','ma-nguon/database','.github','cau-hinh'],cwd=ROOT,text=True)
        require(not dirty.strip(),'build source is dirty')
        require(a.source_git_context and '#'+commit+':ma-nguon/order-app' in a.source_git_context,'build requires immutable Git context for exact source/provenance; local unpublished checkpoint cannot be substituted')
        # One BuildKit build, two exports of the same OCI candidate. Verify bytes, never trust a mutable tag.
        execute(['docker','buildx','build','--platform','linux/amd64','--provenance=mode=max','--metadata-file',str(root/'build-metadata.json'),'--label','org.opencontainers.image.revision='+commit,'--label','orderflow.source_snapshot='+snapshot,'--output','type=registry,name='+a.image+',oci-mediatypes=true','--output','type=oci,dest='+str(root/'candidate.tar')+',oci-mediatypes=true',a.source_git_context],root)
        metadata=json.loads((root/'build-metadata.json').read_text());index_digest=metadata.get('containerimage.digest');require(isinstance(index_digest,str),'build metadata digest missing')
        immutable=repository+'@'+index_digest
        index_bytes=capture_manifest(immutable);index=json.loads(index_bytes)
        choices=[x for x in index.get('manifests',[]) if x.get('platform',{}).get('os')=='linux' and x.get('platform',{}).get('architecture')=='amd64']
        require(len(choices)==1,'single linux/amd64 manifest required');platform_digest=choices[0]['digest']
        platform_bytes=capture_manifest(repository+'@'+platform_digest);platform=json.loads(platform_bytes);image_id=platform['config']['digest']
        (root/'registry-index.json').write_bytes(index_bytes);(root/'registry-manifest.json').write_bytes(platform_bytes)
        execute(['docker','pull',immutable],root)
        if a.public_key:shutil.copyfile(a.public_key,root/'cosign.pub')
        c={'contract':'reference-1','run_id':root.name,'source_commit':commit,'source_snapshot':snapshot,'archive_path':'candidate.tar','archive_sha256':sha(root/'candidate.tar'),'registry_index_path':'registry-index.json','manifest_digest':index_digest,'platform_manifest_digest':platform_digest,'artifact_subject':immutable.rsplit('@',1)[1],'config_digest':image_id,'image_reference':immutable,'registry_manifest_path':'registry-manifest.json','public_key_path':'cosign.pub','bundle_path':'candidate.bundle.json','evidence_kind':'BUILD_EXECUTION','trust_status':'PUBLIC_KEY_PROVIDED_NOT_AUTOMATICALLY_APPROVED' if a.public_key else 'NOT_PROVIDED'}
        verify_archive(root,c);verify_registry(root,c)
        (root/'candidate.json').write_bytes((json.dumps(c,indent=2)+'\n').encode());return 0
    except Exception as exc:print('ARTIFACT BLOCKED: '+str(exc));return 2
if __name__=='__main__':raise SystemExit(main())
