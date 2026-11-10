#!/usr/bin/env python3
"""Freeze v4 launch scripts. Reuse v2 optimization settings and original stage3."""
from pathlib import Path
import json
from build_targeted_v4_components import ROOT,OUT
REMOTE='/C20545/kev-08b-official-repro-20261026'

def main():
    (OUT/'preflight.py').write_text('''import json, sys
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
assert len(dev)==330 and not rejected
result={'training_contexts_including_replay':len(rows),'training_questions':sum(len(r['questions']) for r in rows),'development_contexts':len(dev),'rejected_development':rejected,'context':training_context(7552)}
Path(output).write_text(json.dumps(result,indent=2)+'\\n')
print(json.dumps(result),flush=True)
''')
    (OUT/'evaluate_development.py').write_text('''import json,sys,hashlib,time
from pathlib import Path
from kev.data import load_records
from kev.model import training_context
from kev.predictors import LocalPredictor
from kev.checkpoint import LoadOptions
from kev.benchmark import evaluate_records
run,data,out=sys.argv[1:]
predictor=LocalPredictor(run,'cuda',LoadOptions.from_env(),context={**training_context(7552),'truncate':False})
start=time.time()
report,_=evaluate_records(load_records(data),predictor,out,heldout_sources=(),skip_overlong=False)
report.update(run=run,data=data,data_sha256=hashlib.sha256(Path(data).read_bytes()).hexdigest(),elapsed_seconds=time.time()-start,scope='same-generator development; not independent heldout')
Path(out,'report.json').write_text(json.dumps(report,indent=2)+'\\n')
print(json.dumps({'clean':report['clean'],'coverage':report['coverage']}),flush=True)
''')
    for model,old,original,base,revision,gpu in [
        ('qwen3','qwen3','qwen3-06b-20261026','/C20545/models/Qwen3-0.6B-Base','local-model-sha256-cd2a512003e2f9f3cd3c32a9c3573f820bb28c940f73c57b1ddaa983d9223eba',1),
        ('qwen35','qwen35','replica-20261026','Qwen/Qwen3.5-0.8B-Base','dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68',2)]:
        oldtext=(ROOT/f'artifacts/kev_training_eval_20261026/targeted_v2_all7_compact/launch_{old}_stage4.sh').read_text()
        train=oldtext[oldtext.index('exec env '):].replace('exec env ','env ',1).replace('targeted_v2_all7_compact/train.jsonl',OUT.name+'/train.jsonl')
        oldrun='qwen3-06b-20261029-targeted-v2-all7-compact' if model=='qwen3' else 'replica-20261029-targeted-v2-all7-compact'
        newrun=f'{model}-20261030-targeted-v4'
        train=train.replace(oldrun,newrun)
        script=f'''#!/usr/bin/env bash
set -euo pipefail
ROOT={REMOTE}
DATA="$ROOT/{OUT.name}"
RUN="$ROOT/runs/{newrun}"
test ! -e "$RUN"
mkdir "$RUN"
trap 'code=$?; if [ "$code" -ne 0 ]; then printf "failed exit=%s\\n" "$code" > "$RUN/status.txt"; fi' EXIT
export CUDA_VISIBLE_DEVICES={gpu} HF_HOME="$ROOT/hf" HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1
export PYTHONPATH="$ROOT/stages/stage3${{PYTHONPATH:+:$PYTHONPATH}}"
cd "$ROOT/stages/stage3"
printf 'preflight\\n' > "$RUN/status.txt"
"$ROOT/python.sh" "$DATA/preflight.py" '{base}' '{revision}' "$DATA" "$ROOT/evals/v7/decision-v7" "$RUN/preflight.json"
printf 'development_before\\n' > "$RUN/status.txt"
"$ROOT/python.sh" "$DATA/evaluate_development.py" "$ROOT/runs/{original}/stage3" "$DATA/development.jsonl" "$RUN/development-before"
printf 'training\\n' > "$RUN/status.txt"
{train}
printf 'development_after\\n' > "$RUN/status.txt"
"$ROOT/python.sh" "$DATA/evaluate_development.py" "$RUN/stage4" "$DATA/development.jsonl" "$RUN/development-after"
printf 'hard_v1\\n' > "$RUN/status.txt"
"$ROOT/python.sh" -m kev.benchmark --run "$RUN/stage4" --suite "$ROOT/evals/hard-v1" --allow-test --device cuda --out "$RUN/eval-hard-v1"
printf 'devtools_v1\\n' > "$RUN/status.txt"
"$ROOT/python.sh" -m kev.benchmark --run "$RUN/stage4" --suite "$ROOT/evals/devtools-v1" --allow-test --device cuda --out "$RUN/eval-devtools-v1"
printf 'complete\\n' > "$RUN/status.txt"
'''
        (OUT/f'launch_{model}.sh').write_text(script)
    print(str(OUT))

if __name__=='__main__':main()
