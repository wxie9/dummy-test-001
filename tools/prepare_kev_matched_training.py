#!/usr/bin/env python3
"""Prepare v9: 1500 base contexts, 1020 extra views, 6000 replay records."""
import hashlib
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/kev_training_eval_20261026'
OUT = BASE / 'targeted_v9_matched_20261030'
SOURCE = BASE / 'targeted_v7_lr5_20261030'


def main():
    assert not (OUT / 'launch.json').exists()
    preflight = (SOURCE / 'preflight.py').read_text().replace('len(rows)==7500', 'len(rows)==8520').replace('len(dev)==334', 'len(dev)==562')
    extra = '''
import hashlib, random
from collections import Counter
from kev.data import augment, none_pair, source_seed
d=Path(folder); frozen=json.loads((d/'manifest.json').read_text())
for key,spec in frozen['files'].items():
 assert hashlib.sha256((d/(key+'.jsonl')).read_bytes()).hexdigest()==spec['sha256']
 records=load_records(str(d/(key+'.jsonl')))
 assert len(records)==spec['records'] and sum(len(r['questions']) for r in records)==spec['questions']
 assert all(fits(materialize(r),tok,**training_context(7552)) for r in records)
base_rows=load_records(str(d/'train_base.jsonl'))
assert Counter(r['_meta']['family'] for r in base_rows)=={'probability':350,'multihop':270,'insufficient':280,'policy':300,'tool_routing':100,'temporal':100,'injection':100}
targeted=load_records(str(d/'train.jsonl')); lookup={r['_meta']['id']:r for r in targeted}
targeted_ids=set(lookup)
assert targeted_ids.issubset({r['_meta']['id'] for r in rows})
replay_ids=[r['_meta']['id'] for r in rows if r['_meta']['id'] not in targeted_ids]
assert len(replay_ids)==6000
retained={'tool_routing','temporal','injection'}
old_lines=(d.parent/'targeted_v7_20261030/train.jsonl').read_text().splitlines()
keep=lambda lines:{json.loads(l)['_meta']['id']:l for l in lines if json.loads(l)['_meta']['family'] in retained}
assert keep(old_lines)==keep((d/'train_base.jsonl').read_text().splitlines())
pairmap=json.loads((d/'pair_mapping.json').read_text())['train']; assert len(pairmap)==1020
for pair in pairmap:
 a,b=lookup[pair['base_id']],lookup[pair['matched_id']]
 for qid,x in a['questions'].items():
  y=b['questions'][qid]
  assert {k:v for k,v in x.items() if k not in ['label','target']}=={k:v for k,v in y.items() if k not in ['label','target']}
checked=0
for r in targeted:
 rng=random.Random(source_seed(101,"0:"+r['_meta']['id']))
 variants=[augment(r,rng,p_none=.1,p_none_distract=.12,p_distract=.15)]
 if rng.random()<.25: variants+=none_pair(r,rng)
 for v in variants:
  for qid,q in r['questions'].items():
   if q['type']=='choice' and q.get('target') is not None:
    aq=v['questions'][qid]
    assert dict(q['criteria'])==dict(aq['criteria']) and q['label']==aq['label'] and q['target']==aq['target']
    checked+=1
result.update(base_contexts=1500,additional_views=1020,retained_byte_identical=300,matched_groups=1020,matched_choice_augmentation_checks=checked,expected_optimizer_steps=1065,replay_records=len(replay_ids),data_sha256=frozen['files']['train']['sha256'],augmentation_note='Candidate values preserved; independently seeded permutations need not have the same order across paired records.')
'''
    preflight = preflight.replace('Path(output).write_text', extra + '\nPath(output).write_text')
    (OUT / 'preflight.py').write_text(preflight)
    (OUT / 'evaluate_development.py').write_bytes((BASE / 'targeted_v8_steps_20261030/evaluate_development.py').read_bytes())
    gate = '''import json,sys,hashlib
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
(r/'baseline_gate.json').write_text(json.dumps({'passed':True,'retained_original_stage3_questions_exact':90,'development_questions':856,'probe_questions':190,'full_training_questions':3990},indent=2)+'\\n')
print('Original stage3 baseline verified; complete coverage.',flush=True)
'''
    (OUT / 'verify_baseline.py').write_text(gate)
    for model, original in [('qwen3','qwen3-06b-20261026'),('qwen35','replica-20261026')]:
        s=(SOURCE/('launch_'+model+'.sh')).read_text().replace(SOURCE.name,OUT.name).replace('targeted-v7-lr5','targeted-v9-matched').replace('--lr 5e-5','--lr 1e-5')
        marker="printf 'training\\n' > \"$RUN/status.txt\""
        before="printf 'full_train_before\\n' > \"$RUN/status.txt\"\n"+f'"$ROOT/python.sh" "$DATA/evaluate_development.py" "$ROOT/runs/{original}/stage3" "$DATA/train.jsonl" "$RUN/full-train-before"\n'+f'"$ROOT/python.sh" "$DATA/verify_baseline.py" "$RUN" "$DATA" {model} {original}\n'
        assert marker in s
        (OUT/('launch_'+model+'.sh')).write_text(s.replace(marker,before+marker))
    m=json.loads((OUT/'manifest.json').read_text());m['status']='prepared_remote_preflight_pending'
    m['evaluation_plan']={'before':'Original stage3 on all 2520 training records, 562 development records, 140 training probes; exact retained 90-question baseline check.', 'after':'Same inputs plus full hard-v1 and devtools-v1. Report repaired and newly broken cases for each of seven categories.', 'success':'Both models improve all seven real categories; training accuracy alone is insufficient.'}
    (OUT/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
    # Use a truthful generic scope, without changing archived earlier audit scripts.
    audit=(ROOT/'tools/audit_kev_none_augmentation.py').read_text().replace('current training preflight verified all 7500 records fit.','token fit must be established by the separate preflight report.')
    (OUT/'audit_augmentation.py').write_text(audit)
    (OUT/'snapshot.py').write_bytes((ROOT/'tools/snapshot_kev_control.py').read_bytes())
    with tarfile.open(OUT/'inputs.tar.gz','w:gz') as t:
        for p in sorted(OUT.iterdir()):
            if p.suffix in ['.py','.sh','.json','.jsonl']:t.add(p,arcname=OUT.name+'/'+p.name,recursive=False)
    print('prepared inputs sha256',hashlib.sha256((OUT/'inputs.tar.gz').read_bytes()).hexdigest())


if __name__=='__main__':main()
