#!/usr/bin/env python3
"""Persist v5 terminal status only from validated complete evidence."""
import json
from datetime import datetime, timezone
from build_targeted_v5 import OUT

def main():
    comparison=json.loads((OUT/'comparison-seven.json').read_text())
    state=json.loads((OUT/'run_status.json').read_text())
    state['previous_live_check_utc']=state.pop('checked_at_utc')
    state.pop('checked_at_asia_shanghai',None);state.pop('ssh_session_id',None)
    state['finalized_at_utc']=datetime.now(timezone.utc).isoformat()
    state['status']='training_and_evaluation_complete_goal_unachieved'
    for model in ['qwen3','qwen35']:
        run=OUT/'evidence/runs'/f'{model}-20261030-targeted-v5'
        assert (run/'status.txt').read_text().strip()=='complete'
        s=state[model]
        for k in ['pipeline_pid','training_pid','last_observed_step']:s.pop(k,None)
        s['completed_steps']=comparison['models'][model]['training']['optimizer_steps']
        s['training_wall_seconds']=comparison['models'][model]['training']['wall_seconds']
        s['seven_pooled']=comparison['models'][model]['seven_pooled']
    state['train_probe']['after']='complete, full paired evidence downloaded'
    state['next']='A separate fixed-data 3-epoch experiment tests acquisition strength; never restart completed v5 or report all seven improved.'
    (OUT/'run_status.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
    print(state['status'])

if __name__=='__main__':main()
