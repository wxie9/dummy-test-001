import json, sys
from pathlib import Path
from kev.data import load_records, materialize
from kev.model import load_tokenizer, fits, training_context
base, revision, data, output = sys.argv[1:]
tok = load_tokenizer(base, revision=revision)
rows = load_records(data)
context = training_context(7552)
rejected = [r['_meta']['id'] for r in rows if not fits(materialize(r), tok, **context)]
summary = {'records':len(rows),'questions':sum(len(r['questions']) for r in rows), 'rejected':rejected, 'context':context, 'max_state_tokens':max(len(tok.encode(r['state'], add_special_tokens=False)) if isinstance(r['state'],str) else len(tok.encode(json.dumps(r['state']),add_special_tokens=False)) for r in rows)}
Path(output).write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary), flush=True)
assert len(rows)==128 and not rejected, 'Pilot must train every planned context without silent filtering'
