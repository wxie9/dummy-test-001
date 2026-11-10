import json, sys
from pathlib import Path
from types import SimpleNamespace
from kev.model import load_tokenizer, fits, training_context
from kev.data import load_records, materialize
from kev.train import training_requests
from kev.suite import read_manifest
base, revision, folder, suite, output = sys.argv[1:]
tok=load_tokenizer(base, revision=revision)
a=SimpleNamespace(data=folder+'/train.jsonl',suite=suite,replay=6000,seed=101,max_state=7552,train_sources='',public_frac=1.0,synthetic_repeat=1)
manifest=read_manifest(suite)
rows=training_requests(a,tok,manifest,manifest['holdout_sources'])
assert len(rows)==8520, 'A planned training context was filtered'
dev=load_records(folder+'/development.jsonl')
rejected=[r['_meta']['id'] for r in dev if not fits(materialize(r),tok,**training_context(7552))]
assert len(dev)==562 and not rejected
result={'training_contexts_including_replay':len(rows),'training_questions':sum(len(r['questions']) for r in rows),'development_contexts':len(dev),'rejected_development':rejected,'context':training_context(7552)}

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

Path(output).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
