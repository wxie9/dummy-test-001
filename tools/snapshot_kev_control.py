#!/usr/bin/env python3
"""Observe existing remote experiment processes; never launch or restart jobs."""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('data',type=Path);a=ap.parse_args();data=a.data.resolve()
    state=json.loads((data/'run_status.json').read_text());procs={}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:procs[int(p.name)]=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
        except OSError:continue
    compact={}
    for name,e in state['models'].items():
        run=Path(e['run']);e['status']=(run/'status.txt').read_text().strip()
        e['pipeline_live']=('launch_'+name+'.sh') in procs.get(e['pipeline_pid'],'')
        e['training_pids']=[pid for pid,cmd in procs.items() if '-m kev.train ' in cmd and str(run)+'/stage4' in cmd]
        e['training_live']=bool(e['training_pids'])
        log=(data/(name+'-pipeline.log')).read_text();e['log_tail']=log[-1300:]
        steps=re.findall(r'ep(\d+) step (\d+)/(\d+) loss ([\d.]+).*?([\d.]+)s/rec',log)
        if steps:
            epoch,step,total,loss,speed=steps[-1]
            e.update(last_observed_epoch=int(epoch),last_observed_step=int(step),steps_per_epoch=int(total),last_logged_loss=float(loss),last_logged_seconds_per_record=float(speed))
        metrics=run/'stage4/training_metrics.json'
        if metrics.exists():
            measured=json.loads(metrics.read_text());e['completed_steps']=measured['optimizer_steps'];e['training_wall_seconds']=measured['wall_seconds']
        for kind in ['development-before','train-probe-before','full-train-before','development-after','train-probe-after','full-train-after','development-steps-before','development-steps-after','eval-hard-v1','eval-devtools-v1']:
            report=run/kind/'report.json'
            if report.exists():
                r=json.loads(report.read_text());c=r['coverage']
                assert c['requested_records']==c['evaluated_records'] and c['requested_questions']==c['evaluated_questions'] and c['rejected_records']==c['truncated_records']==0
                e.setdefault('completed_evaluation_coverage',{})[kind]=c
        compact[name]={k:e[k] for k in ['status','pipeline_pid','pipeline_live','training_pids','training_live','last_observed_step'] if k in e}
    state['checked_at_utc']=datetime.now(timezone.utc).isoformat()
    state['status']='all_pipelines_complete' if all(e['status']=='complete' for e in state['models'].values()) else 'active_or_attention_required'
    (data/'run_status.json').write_text(json.dumps(state,indent=2)+'\n')
    print(json.dumps({'checked_at_utc':state['checked_at_utc'],'models':compact}))

if __name__=='__main__':main()
