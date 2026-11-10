#!/usr/bin/env python3
"""Compare label-preserving input changes at fixed checkpoints."""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from summarize_kev_training_fit_audit import counts

def main():
    ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path);args=ap.parse_args();p=args.directory.resolve()
    e=p/'evidence';launch=json.loads((p/'launch.json').read_text());manifest=json.loads((p/'manifest.json').read_text())
    raw=[json.loads(l) for l in (p/'probe.jsonl').read_text().splitlines()];byid={r['_meta']['id']:r for r in raw}
    mapping={r['id']:r for r in json.loads((p/'mapping.json').read_text())}
    expected=[(r['_meta']['id'],q) for r in raw for q in r['questions']]
    result={'scope':'Matched inference-only input interventions on previously trained cases. Not retraining, official test improvement, or independent generalization. Policy excerpt jointly simplifies retrieval and reduces length.','jobs':{},'input_sha256':hashlib.sha256((p/'probe.jsonl').read_bytes()).hexdigest()}
    lines=['# 输入表述诊断','',result['scope'],'','|checkpoint|改动|原输入正确|改后正确|子问数|修复/新增错|','|---|---|---:|---:|---:|---|']
    for name,job in launch['jobs'].items():
        root=job['checkpoint'].split('/runs/')[0];base=e/Path(job['baseline']).relative_to(root)
        before=json.loads((base/'rows.json').read_text());bi={(r['id'],r['question']):r for r in before};assert len(bi)==len(before)
        folder=e/p.name/name;report=json.loads((folder/'report.json').read_text());after=json.loads((folder/'rows.json').read_text())
        assert report['run']==job['checkpoint'] and report['data_sha256']==manifest['probe_sha256']==result['input_sha256']
        c=report['coverage'];assert c['requested_records']==c['evaluated_records']==525 and c['requested_questions']==c['evaluated_questions']==1050 and c['rejected_records']==c['truncated_records']==0
        assert [(r['id'],r['question']) for r in after]==expected
        groups=defaultdict(list);unchanged=0;allrows=[]
        for r in after:
            info=mapping[r['id']];b=bi[(info['original_id'],r['question'])]
            assert (b['keys'],b['label'],b['source'])==(r['keys'],r['label'],r['source'])
            if info['state_unchanged']:assert b['p']==r['p'];unchanged+=1
            pick=lambda z:max(range(len(z['p'])),key=z['p'].__getitem__)
            row={'id':info['original_id'],'before_ok':pick(b)==b['label'],'after_ok':pick(r)==r['label']}
            variant=info['variant'];allrows.append({**row,'question':r['question'],'variant':variant})
            axes=[('variant',variant),('question',variant+'/'+r['question']),('subtype',variant+'/'+info['subtype']+'/'+r['question'])]
            if info['family']=='policy':
                payment='positive' if info['subtype'].startswith('pay_') else 'zero'
                axes.append(('payment',payment+'/'+r['question']))
                axes.append(('cover_count',str(byid[r['id']]['_meta']['facts']['cover_count'])+'/'+r['question']))
            else:
                axes.append(('scale',variant+'/'+str(info['count_divisor'])+'/'+r['question']))
            for axis,value in axes:groups[(axis,value)].append(row)
        assert unchanged==84
        summaries=[{'axis':axis,'value':value,**counts(rs)} for (axis,value),rs in sorted(groups.items())]
        result['jobs'][name]={'subgroups':summaries,'unchanged_questions_exactly_reproduced':unchanged,'elapsed_seconds':report['elapsed_seconds']}
        for g in summaries:
            if g['axis']=='variant':lines.append(f"|{name}|{g['value']}|{g['before_correct']}|{g['after_correct']}|{g['questions']}|{g['repaired']}/{g['newly_wrong']}|")
    (p/'comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (p/'输入诊断结果.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))
    for name,v in result['jobs'].items():
        print(name,'policy payment',[(g['value'],g['before_correct'],g['after_correct'],g['questions']) for g in v['subgroups'] if g['axis']=='payment'])

if __name__=='__main__':main()
