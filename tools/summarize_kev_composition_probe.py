#!/usr/bin/env python3
"""Analyze controlled depth variants and privileged eligibility diagnostics."""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

def read(p):return json.loads(p.read_text())
def pick(r):return max(range(len(r['p'])),key=r['p'].__getitem__)
def correct(r):return pick(r)==r['label']
def money(s):return float(s.replace('$','').replace(',',''))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path);a=ap.parse_args();p=a.directory.resolve();e=p/'evidence'
    manifest=read(p/'manifest.json');launch=read(p/'launch.json');raw=[json.loads(l) for l in (p/'probe.jsonl').read_text().splitlines()]
    byid={r['_meta']['id']:r for r in raw};mapping={r['id']:r for r in read(p/'mapping.json')};expected=[(r['_meta']['id'],q) for r in raw for q in r['questions']]
    h=hashlib.sha256((p/'probe.jsonl').read_bytes()).hexdigest();assert h==manifest['probe_sha256']
    result={'scope':manifest['scope'],'limits':manifest['limits'],'input_sha256':h,'jobs':{}}
    lines=['# 组合能力诊断','',manifest['scope'],'','## 传播距离','',
           '每个距离含30个共享图组；每组同时包含目标会失败和被软边阻断两种情形。各距离沿用相同候选、顺序、节点名和边数。','',
           '|checkpoint|实际距离|会失败正确/30|被阻断正确/30|两种均对/30|修改硬软边后答案变化/30|','|---|---:|---:|---:|---:|---:|']
    policy_lines=['','## 已知资格后的金额判断','',
                  '以下120道均来自原训练集的正赔付情境。资格已知是一项额外的正确前提，不能当作正式评测或部署时的成绩。','',
                  '|checkpoint|原金额正确/120|资格已知正确/120|含0候选原选0/93|资格已知选0/93|修复/新增错|','|---|---:|---:|---:|---:|---|']
    for name,j in launch['jobs'].items():
        folder=e/p.name/name;rpt=read(folder/'report.json');rows=read(folder/'rows.json')
        assert rpt['run']==j['checkpoint'] and rpt['data_sha256']==h
        c=rpt['coverage'];assert c['requested_records']==c['evaluated_records']==480 and c['requested_questions']==c['evaluated_questions']==720 and c['rejected_records']==c['truncated_records']==0
        assert [(r['id'],r['question']) for r in rows]==expected
        root=j['checkpoint'].split('/runs/')[0];baseline=read(e/Path(j['baseline']).relative_to(root)/'rows.json');bi={(r['id'],r['question']):r for r in baseline};assert len(bi)==len(baseline)
        graph=defaultdict(dict);policy=defaultdict(dict);control_diffs=[];control_flips=[];sources={}
        for r in rows:
            info=mapping[r['id']];q=byid[r['id']]['questions'][r['question']]
            assert set(r['keys'])==set(q['criteria']) and r['keys'][r['label']]==q['label']
            if info['family']=='graph_probe':graph[(info['group'],info['depth'])][info['blocked']]=r
            else:
                if info['variant']=='original':
                    b=bi[(info['original_id'],r['question'])]
                    assert (b['keys'],b['label'])==(r['keys'],r['label'])
                    control_diffs.append(max(abs(x-y) for x,y in zip(b['p'],r['p'])))
                    if pick(b)!=pick(r):control_flips.append({'id':info['original_id'],'question':r['question'],'max_abs_probability_difference':control_diffs[-1]})
                if r['question']=='amount':policy[info['group']][info['variant']]=r;sources[info['group']]=info
        assert len(control_diffs)==240 and len(graph)==120 and len(policy)==120
        gs=defaultdict(Counter)
        for (group,depth),variants in graph.items():
            assert set(variants)=={False,True};yes,no=variants[False],variants[True];g=gs[depth]
            assert yes['keys']==no['keys']
            g['groups']+=1;g['affected_correct']+=correct(yes);g['blocked_correct']+=correct(no)
            g['both_correct']+=correct(yes) and correct(no);g['prediction_changed']+=pick(yes)!=pick(no)
        ps=Counter();pstrata=defaultdict(Counter);details=[]
        for group,views in policy.items():
            assert set(views)=={'original','eligibility_given'};before,after=views['original'],views['eligibility_given'];info=sources[group]
            assert (before['keys'],before['label'])==(after['keys'],after['label'])
            q=byid[before['id']]['questions']['amount'];before_zero=money(q['criteria'][before['keys'][pick(before)]])==0;after_zero=money(q['criteria'][after['keys'][pick(after)]])==0
            increments={'contexts':1,'original_correct':int(correct(before)),'eligibility_given_correct':int(correct(after)),
                        'original_predicted_zero':int(before_zero),'eligibility_given_predicted_zero':int(after_zero),
                        'repaired':int(not correct(before) and correct(after)),'newly_wrong':int(correct(before) and not correct(after))}
            ps.update(increments);pstrata['zero_offered='+str(info['zero_offered'])].update(increments)
            details.append({'id':group,**increments})
        assert pstrata['zero_offered=True']['contexts']==93
        entry={'graph_by_depth':{str(k):dict(v) for k,v in sorted(gs.items())},'policy':dict(ps),'policy_strata':{k:dict(v) for k,v in pstrata.items()},'policy_cases':details,
               'original_input_control':{'questions':len(control_diffs),'same_top_choice':len(control_diffs)-len(control_flips),'max_abs_probability_difference':max(control_diffs),'flips':control_flips},'elapsed_seconds':rpt['elapsed_seconds']}
        result['jobs'][name]=entry
        for depth,g in sorted(gs.items()):lines.append(f"|{name}|{depth}|{g['affected_correct']}|{g['blocked_correct']}|{g['both_correct']}|{g['prediction_changed']}|")
        z=pstrata['zero_offered=True'];policy_lines.append(f"|{name}|{ps['original_correct']}|{ps['eligibility_given_correct']}|{z['original_predicted_zero']}|{z['eligibility_given_predicted_zero']}|{ps['repaired']}/{ps['newly_wrong']}|")
    lines+=policy_lines+['','原输入控制的概率差和选项翻转见comparison.json；额外资格前提与问法一起变化，此诊断不能独立证明资格推理是唯一原因。图形各变体相关，不能按240个独立样本计算置信度。']
    (p/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');(p/'组合诊断结果.md').write_text('\n'.join(lines)+'\n');print('\n'.join(lines))

if __name__=='__main__':main()
