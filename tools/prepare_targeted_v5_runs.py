#!/usr/bin/env python3
"""V5 keeps v4 training settings; only data changes. No checkpoint chaining."""
import json
from build_targeted_v5 import OLD, OUT

def main():
    manifest=json.loads((OUT/'manifest.json').read_text())
    assert manifest['files']['train']['contexts']==1500
    assert manifest['files']['development']['contexts']==340
    for name in ['launch_qwen3.sh','launch_qwen35.sh','preflight.py','evaluate_development.py']:
        text=(OLD/name).read_text().replace('targeted_v4_20261030','targeted_v5_20261030').replace('targeted-v4','targeted-v5')
        if name=='preflight.py':text=text.replace('len(dev)==330','len(dev)==340')
        (OUT/name).write_text(text)
    manifest['training_plan']={'epochs':1,'seed':101,'lr':1e-5,'lora':16,'batch':4,'accum':2,'replay':6000,
        'init':'original pre-targeted stage3','augmentation':'same as v4/v2','purpose':'data-revision comparison at fixed training settings'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(str(OUT))

if __name__=='__main__':main()
