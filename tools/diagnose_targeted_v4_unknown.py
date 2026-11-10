#!/usr/bin/env python3
"""Audit unknown-answer regressions without changing frozen training inputs."""
import json
from pathlib import Path
from summarize_targeted_v4 import paired, stats

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/kev_training_eval_20261026/targeted_v4_20261030'

def main():
    metadata = {
        r['_meta']['id']: r['_meta']
        for r in map(json.loads, (OUT / 'development.jsonl').read_text().splitlines())
    }
    results = {}
    for model in ('qwen3', 'qwen35'):
        run = OUT / 'evidence/runs' / f'{model}-20261030-targeted-v4'
        before = json.loads((run / 'development-before/rows.json').read_text())
        after = json.loads((run / 'development-after/rows.json').read_text())
        rows = [r for r in paired(before, after) if metadata[r['id']]['family'] == 'insufficient']
        assert len(rows) == 60
        results[model] = {
            variant: stats([r for r in rows if metadata[r['id']]['facts']['variant'] == variant])
            for variant in ('yes', 'no', 'unknown', 'nondeciding')
        }
    report = {
        'models': results,
        'observation': 'Unknown-answer accuracy decreases on the generated development set for both models, despite higher aggregate insufficient-information accuracy.',
        'causal_status': 'Label balance and lack of matched pairs are hypotheses; this audit alone does not establish causality.',
        'next_intervention': 'Build deciding-variable present/missing matched pairs and nondeciding-variable controls. Keep siblings in one split. Compare from original stage3, never from v4.',
    }
    (OUT / 'unknown_development_diagnostics.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    comparison = json.loads((OUT / 'comparison-seven.json').read_text())
    status = json.loads((OUT / 'run_status.json').read_text())
    status['status'] = 'training_and_evaluation_complete_goal_unachieved'
    status['status_basis'] = 'Downloaded complete status, training metrics, full before/after prediction rows and coverage reports; see evidence/runs.'
    status['previous_live_observation_at_utc'] = status.pop('checked_at_utc', None)
    status['previous_live_observation_at_asia_shanghai'] = status.pop('checked_at_asia_shanghai', None)
    status.pop('ssh_session_id', None)
    for model in ('qwen3', 'qwen35'):
        result = comparison['models'][model]
        status[model].pop('pipeline_pid', None)
        status[model].pop('training_pid', None)
        status[model].pop('last_observed_step', None)
        status[model]['completed_steps'] = result['training']['optimizer_steps']
        status[model]['training_wall_seconds'] = result['training']['wall_seconds']
        status[model]['seven_pooled'] = result['seven_pooled']
    status['goal_achieved'] = False
    status['next'] = 'Diagnose and repair unknown-answer, probability, multihop and positive-payment weaknesses. Do not restart the completed v4 runs or claim all seven categories improved.'
    (OUT / 'run_status.json').write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n')
    for model, variants in results.items():
        print(model, {k: (v['before_correct'], v['after_correct'], v['questions']) for k, v in variants.items()})

if __name__ == '__main__':
    main()
