import json
import random
import hashlib
from pathlib import Path

root = Path(__file__).resolve().parents[1] / 'artifacts/kev_training_eval_20261026'
old = root / 'targeted_v5_20261030'
out = root / 'targeted_v6_20261030'
for name in ['launch_qwen3.sh', 'launch_qwen35.sh', 'preflight.py', 'evaluate_development.py']:
    text = (old/name).read_text().replace('targeted_v5_20261030','targeted_v6_20261030').replace('targeted-v5','targeted-v6')
    if name == 'preflight.py': text = text.replace('len(dev)==340','len(dev)==336')
    if name.startswith('launch_'):
        checkpoint = 'qwen3-06b-20261026' if name == 'launch_qwen3.sh' else 'replica-20261026'
        before = "printf 'training\\n' > \"$RUN/status.txt\""
        text = text.replace(before, "printf 'train_probe_before\\n' > \"$RUN/status.txt\"\n" +
            '"$ROOT/python.sh" "$DATA/evaluate_development.py" "$ROOT/runs/'+checkpoint+'/stage3" "$DATA/train_probe.jsonl" "$RUN/train-probe-before"\n'+before)
        after = "printf 'hard_v1\\n' > \"$RUN/status.txt\""
        text = text.replace(after, "printf 'train_probe_after\\n' > \"$RUN/status.txt\"\n" +
            '"$ROOT/python.sh" "$DATA/evaluate_development.py" "$RUN/stage4" "$DATA/train_probe.jsonl" "$RUN/train-probe-after"\n'+after)
    (out/name).write_text(text)
rows = [json.loads(line) for line in (out/'train.jsonl').read_text().splitlines()]
probe = []
for family in sorted({r['_meta']['family'] for r in rows}):
    pool = sorted([r for r in rows if r['_meta']['family']==family], key=lambda r:r['_meta']['id'])
    probe.extend(random.Random('v6-train-probe/'+family).sample(pool,20))
p = out/'train_probe.jsonl'
p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in probe))
m = json.loads((out/'manifest.json').read_text())
m['training_plan'] = dict(epochs=1,seed=101,lr=1e-5,lora=16,batch=4,accum=2,replay=6000,
    init='original pre-targeted stage3',purpose='fixed-epoch data-revision experiment; not guaranteed gain')
m['train_probe'] = dict(contexts=140,subquestions=sum(len(r['questions']) for r in probe),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
(out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
print(m['train_probe'])
