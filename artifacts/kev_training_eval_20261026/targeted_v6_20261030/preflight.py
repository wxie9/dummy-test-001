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
assert len(rows)==7500, 'A planned training context was filtered'
dev=load_records(folder+'/development.jsonl')
rejected=[r['_meta']['id'] for r in dev if not fits(materialize(r),tok,**training_context(7552))]
assert len(dev)==336 and not rejected
result={'training_contexts_including_replay':len(rows),'training_questions':sum(len(r['questions']) for r in rows),'development_contexts':len(dev),'rejected_development':rejected,'context':training_context(7552)}
Path(output).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
