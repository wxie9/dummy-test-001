#!/usr/bin/env python3
"""Record completed control evidence without asserting the broader goal is met."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def main():
    ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path);ap.add_argument('--version',choices=['v5-guard','v5-3ep','v6','v6-3ep','v6-factmix','v7','v7-lr5','v8-steps','v9-matched'],required=True);ap.add_argument('--next',required=True);a=ap.parse_args()
    p=a.directory;comparison=json.loads((p/'comparison-seven.json').read_text());state=json.loads((p/'run_status.json').read_text())
    for model in ['qwen3','qwen35']:
        run=p/'evidence/runs'/(model+'-20261030-targeted-'+a.version)
        assert (run/'status.txt').read_text().strip()=='complete'
        metrics=json.loads((run/'stage4/training_metrics.json').read_text());assert metrics==comparison['models'][model]['training']
        entry=state.get('models',state)[model];historical={k:entry.pop(k) for k in ['pid','pipeline_pid','training_pid','training_pids','last_observed_step'] if k in entry}
        entry.update(status='complete',pipeline_live=False,training_live=False,historical_processes=historical,
                     completed_steps=metrics['optimizer_steps'],training_wall_seconds=metrics['wall_seconds'],
                     seven_pooled=comparison['models'][model]['seven_pooled'],
                     seven_deltas_pp={k:v['delta_pp'] for k,v in comparison['models'][model]['seven_categories'].items()})
    state['previous_live_check_utc']=state.pop('checked_at_utc',None)
    state.update(finalized_at_utc=datetime.now(timezone.utc).isoformat(),status='training_and_evaluation_complete_goal_not_established',
                 goal_achieved=False,next=a.next,comparison_sha256=hashlib.sha256((p/'comparison-seven.json').read_bytes()).hexdigest())
    (p/'run_status.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
    print(state['status'])


if __name__=='__main__':main()
