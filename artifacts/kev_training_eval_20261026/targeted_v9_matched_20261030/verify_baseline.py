import json,sys,hashlib
from pathlib import Path
run,data,model,original=sys.argv[1:]
r=Path(run);d=Path(data);root=d.parent
for kind,file,n,nq in [('development','development.jsonl',562,856),('train-probe','train_probe.jsonl',140,190),('full-train','train.jsonl',2520,3990)]:
 report=json.loads((r/(kind+'-before')/'report.json').read_text());c=report['coverage']
 assert report['data_sha256']==hashlib.sha256((d/file).read_bytes()).hexdigest()
 assert report['run']==str(root/'runs'/original/'stage3')
 assert c['requested_records']==c['evaluated_records']==n and c['requested_questions']==c['evaluated_questions']==nq
 assert c['rejected_records']==c['truncated_records']==0
retained={x['_meta']['id'] for x in map(json.loads,(d/'development.jsonl').read_text().splitlines()) if x['_meta']['family'] in {'tool_routing','temporal','injection'}}
def subset(path):
 return {(x['id'],x['question']):x for x in json.loads(path.read_text()) if x['id'] in retained}
before=subset(r/'development-before/rows.json');reference=subset(root/'runs'/(model+'-20261030-targeted-v7')/'development-before/rows.json')
assert len(before)==len(reference)==90 and before==reference,'Unchanged original stage3 predictions differ'
(r/'baseline_gate.json').write_text(json.dumps({'passed':True,'retained_original_stage3_questions_exact':90,'development_questions':856,'probe_questions':190,'full_training_questions':3990},indent=2)+'\n')
print('Original stage3 baseline verified; complete coverage.',flush=True)
