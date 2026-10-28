"""M4 registry measurement: fetch bytes by immutable digest, never trust a status string."""
import argparse,json,urllib.request,urllib.parse
from pathlib import Path
from m4_result_adapter import candidate,require,sha,verify_registry,read
def capture_manifest(image_reference):
    repository,digest=image_reference.rsplit('@',1)
    host,name=repository.split('/',1)
    parsed=urllib.parse.urlsplit('http://'+host)
    require(parsed.hostname in ('localhost','127.0.0.1'),'only explicit loopback lab registry is supported')
    request=urllib.request.Request('http://'+host+'/v2/'+name+'/manifests/'+digest,headers={'Accept':'application/vnd.oci.image.index.v1+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json'})
    with urllib.request.urlopen(request,timeout=10) as response:
        require(response.status==200,'registry response status')
        payload=response.read()
    import hashlib
    require('sha256:'+hashlib.sha256(payload).hexdigest()==digest,'registry body digest mismatch')
    return payload
def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--run-dir',required=True);a=p.parse_args()
    try:
        c=candidate(read(a.candidate));root=Path(a.run_dir);require(root.name==c['run_id'],'registry run mismatch')
        body=capture_manifest(c['image_reference'].rsplit('@',1)[0]+'@'+c['platform_manifest_digest'])
        target=root/c['registry_manifest_path']
        if target.exists():require(target.read_bytes()==body,'registry manifest changed')
        else:target.write_bytes(body)
        verify_registry(root,c)
        (root/'registry-execution.json').write_bytes(json.dumps({'run_id':c['run_id'],'source_commit':c['source_commit'],'artifact_subject':c['manifest_digest'],'manifest_sha256':sha(target),'operation':'HTTP_GET_IMMUTABLE_MANIFEST','raw_exit_code':0}).encode())
        return 0
    except Exception as exc:print('REGISTRY BLOCKED: '+str(exc));return 2
if __name__=='__main__':raise SystemExit(main())
