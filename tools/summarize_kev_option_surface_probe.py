#!/usr/bin/env python3
"""Canonical-answer comparison for identical cases with different option text."""
import hashlib
import json
from collections import Counter, defaultdict
from build_kev_option_surface_probe import OUT, V5
from summarize_targeted_v4 import stats

def ok(r):return max(range(len(r['p'])),key=r['p'].__getitem__)==r['label']

def main():
    records=[json.loads(l) for l in (OUT/'probe.jsonl').read_text().splitlines()]
    meta={r['_meta']['id']:r['_meta'] for r in records};assert len(meta)==280
    expected=hashlib.sha256((OUT/'probe.jsonl').read_bytes()).hexdigest()
    output={}
    for model,original in [('qwen3','qwen3-06b-20261026'),('qwen35','replica-20261026')]:
        checkpoints={};repeat={}
        for tag,suffix in [('stage3',original+'/stage3'),('v5',model+'-20261030-targeted-v5/stage4')]:
            folder=OUT/'evidence'/f'{model}-{tag}'
            report=json.loads((folder/'report.json').read_text());assert report['data_sha256']==expected and report['run'].endswith('/'+suffix)
            c=report['coverage'];assert c['requested_records']==c['evaluated_records']==280
            assert c['requested_questions']==c['evaluated_questions']==280 and c['rejected_records']==c['truncated_records']==0
            rows=json.loads((folder/'rows.json').read_text());assert len(rows)==280
            olddir='development-before' if tag=='stage3' else 'development-after'
            oldrows=json.loads((V5/'evidence/runs'/f'{model}-20261030-targeted-v5'/olddir/'rows.json').read_text())
            old={r['id']:r for r in oldrows};variants=defaultdict(dict)
            differences=[];changed=0
            for r in rows:
                m=meta[r['id']];roles=m['canonical_option_roles'];assert roles[r['keys'][r['label']]]==m['correct_role']
                pred=roles[r['keys'][max(range(len(r['p'])),key=r['p'].__getitem__)]]
                item={'id':m['original_id'],'correct':ok(r),'prediction':pred,'gold':m['correct_role'],
                    'p_unknown':sum(p for key,p in zip(r['keys'],r['p']) if roles[key]=='unknown')}
                variants[m['surface_variant']][m['original_id']]=item
                if m['surface_variant']=='original':
                    o=old[m['original_id']];assert r['keys']==o['keys'] and r['label']==o['label']
                    differences.extend(abs(p-q) for p,q in zip(r['p'],o['p']));changed+=ok(r)!=ok(o)
            assert all(len(v)==70 for v in variants.values()) and len(variants)==4
            repeat[tag]={'maximum_probability_difference':max(differences),'changed_correctness':changed}
            assert max(differences)<0.001 and changed==0,('original control did not reproduce',model,tag,repeat[tag])
            checkpoints[tag]=variants
        comparison={};surface_effect={}
        for variant in checkpoints['stage3']:
            b=checkpoints['stage3'][variant];a=checkpoints['v5'][variant];assert b.keys()==a.keys()
            rows=[{'id':i,'before_ok':b[i]['correct'],'after_ok':a[i]['correct']} for i in b]
            comparison[variant]={'accuracy':stats(rows),
                'mean_p_unknown_before':sum(x['p_unknown'] for x in b.values())/70,
                'mean_p_unknown_after':sum(x['p_unknown'] for x in a.values())/70,
                'predicted_roles_before':dict(Counter(x['prediction'] for x in b.values())),
                'predicted_roles_after':dict(Counter(x['prediction'] for x in a.values())),
                'by_gold_role':{role:stats([r for r in rows if b[r['id']]['gold']==role]) for role in ['yes','no','unknown']}}
        for tag,variants in checkpoints.items():
            surface_effect[tag]={}
            for variant,v in variants.items():
                if variant=='original':continue
                base=variants['original']
                surface_effect[tag][variant]={'changed_answers':sum(base[i]['prediction']!=v[i]['prediction'] for i in base),
                    'paired_accuracy_change':stats([{'id':i,'before_ok':base[i]['correct'],'after_ok':v[i]['correct']} for i in base])}
        output[model]={'original_control_reproduction':repeat,'training_comparison_by_wording':comparison,'within_checkpoint_wording_effect':surface_effect}
    result={'models':output,'scope':'Same 70 inspected development cases; same semantic gold and option order. Not a heldout result. Unadjusted paired intervals, no training-seed replication.'}
    (OUT/'comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    lines=['# 同题选项措辞诊断','', '| 模型 | 选项表达 | 原stage3正确数 | v5正确数 | 题数 |','|---|---|---:|---:|---:|']
    for m,r in output.items():
        for v,c in r['training_comparison_by_wording'].items():
            s=c['accuracy'];lines.append(f'| {m} | {v} | {s["before_correct"]} | {s["after_correct"]} | 70 |')
    lines+=['','题面、问题、答案含义及选项顺序相同；semantic_keys仅改键名，其余变体仅改描述。原表达控制必须复现既有开发预测，才接受此分析。结果仅说明表达敏感性，不足以证明真实benchmark退步的原因。']
    (OUT/'结果.md').write_text('\n'.join(lines)+'\n');print('\n'.join(lines))

if __name__=='__main__':main()
