import json,sys,hashlib
from pathlib import Path
run,data,model,original=map(str,sys.argv[1:])
r=Path(run);d=Path(data);root=d.parent
for kind,file in [('development','development.jsonl'),('train-probe','train_probe.jsonl')]:
 report=json.loads((r/(kind+'-before')/'report.json').read_text())
 assert report['data_sha256']==hashlib.sha256((d/file).read_bytes()).hexdigest()
 before=json.loads((r/(kind+'-before')/'rows.json').read_text())
 reference=json.loads((root/'runs'/(model+'-20261030-targeted-v7')/(kind+'-before')/'rows.json').read_text())
 assert before==reference,'Original stage3 baseline changed'
step=json.loads((r/'development-steps-before/report.json').read_text());c=step['coverage']
assert step['data_sha256']==hashlib.sha256((d/'development_steps.jsonl').read_bytes()).hexdigest()
assert c['requested_records']==c['evaluated_records']==334 and c['requested_questions']==c['evaluated_questions']==732 and c['rejected_records']==c['truncated_records']==0
assert step['run']==str(root/'runs'/original/'stage3')
(r/'baseline_gate.json').write_text(json.dumps({'passed':True,'original_development_questions':488,'original_probe_questions':185,'step_development_questions':732},indent=2)+'\n')
print('Original baselines identical; step development fully covered.',flush=True)
