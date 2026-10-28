"""EXPLICIT CONTRACT FIXTURE. Dummy key/bundle and injected Cosign never prove a real release."""
import hashlib, io, json, sys, tarfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from m4_result_adapter import sha
from m4_result_adapter import build_result
def write(root,path,value):
    p=Path(root)/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value),encoding='utf-8');return p
def fixture(root, revision='a', snapshot='b', run_id='fixture-run'):
    root=Path(root);root.mkdir(exist_ok=True);run_id=root.name
    layer=b'contract-fixture-layer'
    config={'config':{'Labels':{'org.opencontainers.image.revision':revision*40,'orderflow.source_snapshot':snapshot*64}},'rootfs':{'type':'layers','diff_ids':['sha256:'+hashlib.sha256(layer).hexdigest()]}}
    config_bytes=json.dumps(config).encode();config_digest='sha256:'+hashlib.sha256(config_bytes).hexdigest()
    with tarfile.open(root/'candidate.tar','w') as t:
        for name,b in [('config.json',config_bytes),('layer.tar',layer),('manifest.json',json.dumps([{'Config':'config.json','Layers':['layer.tar']}]).encode())]:
            info=tarfile.TarInfo(name);info.size=len(b);t.addfile(info,io.BytesIO(b))
    manifest=write(root,'registry-manifest.json',{'schemaVersion':2,'mediaType':'application/vnd.oci.image.manifest.v1+json','config':{'digest':config_digest},'layers':[{'digest':'sha256:'+hashlib.sha256(layer).hexdigest()}]})
    manifest_digest='sha256:'+sha(manifest)
    c={'contract':'reference-1','run_id':run_id,'source_commit':revision*40,'source_snapshot':snapshot*64,'archive_path':'candidate.tar','archive_sha256':sha(root/'candidate.tar'),'manifest_digest':manifest_digest,'platform_manifest_digest':manifest_digest,'artifact_subject':manifest_digest,'config_digest':config_digest,'image_reference':'lab.invalid/order-app@'+manifest_digest,'registry_manifest_path':manifest.name,'public_key_path':'cosign.pub','bundle_path':'bundle.json'}
    (root/'cosign.pub').write_text('FIXTURE-NOT-A-REAL-KEY');write(root,'bundle.json',{'fixture':True})
    reports={'GITLEAKS':[],'SBOM':{'spdxVersion':'SPDX-2.3','SPDXID':'SPDXRef-DOCUMENT','packages':[{'name':'fixture'}]},'VULNERABILITY':{'SchemaVersion':2,'ArtifactType':'container_image','ArtifactName':c['image_reference'],'Metadata':{'RepoDigests':[c['image_reference']]},'Results':[{'Target':'fixture','Vulnerabilities':[]}]},'DEPENDENCY':{'packages':[{'name':'flask','version':'3.1.0','approved':True}]},'UNIT_TEST':{'passed':1,'failed':0,'layer':'UNIT_CONTRACT'}}

    from m4_result_adapter import CONTRACT_VERSION, SOURCE_CONTROLS, _execution_subject
    for name,report in reports.items():
        if name=='DEPENDENCY':
            from dependency_policy import load_policy,parse_requirements,ROOT
            policy=ROOT/'cau-hinh/m4/dependency-policy.yml';manifest,allowlist=load_policy(policy)
            report={'schema_version':'1.0','status':'PASS','reason':'ALL_DIRECT_DEPENDENCIES_APPROVED','manifest':manifest.relative_to(ROOT).as_posix(),'scope':'direct','policy_sha256':sha(policy),'manifest_sha256':sha(manifest),'packages':[{'name':n,'version':v,'approved':allowlist.get(n)==v} for n,v,_ in parse_requirements(manifest)],'violations':[]}
        stem=name.lower().replace('_','-');p=write(root,stem+'-report.json',report)
        common={k:c[k] for k in ('source_commit','source_snapshot','run_id')};common.update(contract_version=CONTRACT_VERSION,artifact_subject=None if name in SOURCE_CONTROLS else c['manifest_digest'],execution_subject=_execution_subject(c,name))
        tool={'name':'fixture-tool','version':'1.0'}
        r={**common,'schema_version':'1.0','control_id':name,'execution_status':'SUCCESS','policy_verdict':'PASS','raw_exit_code':0,'reason':'EXPLICIT CONTRACT FIXTURE','tool':tool,'report':{'path':p.name,'sha256':sha(p)},'execution_path':stem+'-execution.json','wrapper_exit_code':None,'policy_exit_code':None}
        e={**common,'raw_exit_code':0,'execution_started':True,'report_sha256':sha(p),'command':['fixture-command'],'tool':tool,'wrapper_exit_code':None,'policy_exit_code':None}
        if name=='GITLEAKS':e['source_context']={'scope':'FULL_HISTORY_AND_WORKTREE','shallow':False,'head_commit':c['source_commit'],'dirty':False,'raw_exit_codes':[0,0],'scanner_integrity':{'fixture':True}}
        write(root,stem+'-result.json',r);write(root,stem+'-execution.json',e)
    return c,sha(root/'cosign.pub')
