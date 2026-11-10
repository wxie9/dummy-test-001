#!/usr/bin/env python3
"""Describe frozen benchmark regressions at mechanism and answer-type level.

Metadata is used only to stratify existing predictions, never as model input.
This reads authored benchmark records but never calls their generators.
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from summarize_targeted_v4 import ROOT, TARGETS, stats

def index_records():
    indexed={}
    for suite in ['hard-v1','devtools-v1']:
        occurrences=Counter()
        for line in (ROOT/'third_party/kev-source-20261025/evals'/suite/'test.jsonl').read_text().splitlines():
            record=json.loads(line);meta=record['_meta']
            for question, spec in record['questions'].items():
                key=(suite,meta['id'],question);occurrences[key]+=1
                indexed[(*key,occurrences[key])]=(record,spec)
    return indexed

def tags(record, question, spec):
    m=record['_meta'];f=m.get('facts',{});source=m['source']
    result={'mechanism':m.get('subtype',m.get('origin','unspecified')),'answer_type':spec['type']}
    if source=='hard_probability':
        result['mechanism']=f.get('kind',result['mechanism'])+('/'+f['ask'] if 'ask' in f else '')
    elif source=='hard_multi_hop':
        result['mechanism']=m['subtype']+('/'+m['rule'] if 'rule' in m else '')
        result['hops']=str(m.get('hops','unspecified'))
        if m['subtype']=='deps':result['soft_dependency']=str(m.get('soft',False))
    elif source=='hard_ambiguous':
        label=spec['label'];shown=spec.get('criteria',{}).get(label,label) if isinstance(spec.get('criteria'),dict) else label
        result['gold_answer']=str(shown if shown is not None else label)
        result['information_state']='unknown' if label=='cannot_be_determined' else 'determinate'
    elif source=='hard_long_policy':
        amount_label=record['questions']['amount']['label']
        amount=f['options_q']['amount'][amount_label]
        result['payment_question']=('positive' if amount>0 else 'zero')+'/'+question
        result['fee_order']=f['fee_order']
    elif source=='when2call':
        result['mechanism']=m.get('bfcl_source','unspecified')
        result['gold_action']=str(spec['label'])
    elif source=='prompt_injection':result['gold_label']=str(spec['label'])
    result['question']=question
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path);a=ap.parse_args()
    indexed=index_records();groups=defaultdict(list);examples=defaultdict(lambda:{'repaired':[],'newly_wrong':[],'still_wrong':[]})
    pairs=[json.loads(l) for l in (a.directory/'paired-seven.jsonl').read_text().splitlines()]
    for p in pairs:
        found=[family for family,(suite,source,question) in TARGETS.items() if p['suite']==suite and p['source']==source and (question is None or question==p['question'])]
        if not found:continue
        assert len(found)==1;family=found[0]
        r,q=indexed[(p['suite'],p['id'],p['question'],p['occurrence'])]
        assert r['_meta']['source']==p['source']
        for axis,value in tags(r,p['question'],q).items():groups[(p['model'],family,axis,value)].append(p)
        kind='repaired' if not p['before_ok'] and p['after_ok'] else 'newly_wrong' if p['before_ok'] and not p['after_ok'] else 'still_wrong' if not p['after_ok'] else None
        if kind:
            key=(p['model'],family);examples[key][kind].append({'id':p['id'],'question':p['question'],'gold_label':q['label'],
                'before_answer':p['before_answer'],'after_answer':p['after_answer'],'mechanisms':tags(r,p['question'],q)})
    output=[]
    for (model,family,axis,value),rows in sorted(groups.items()):
        output.append({'model':model,'family':family,'axis':axis,'value':value,**stats(rows)})
    result={'subgroups':output,'examples':[{'model':m,'family':f,**e} for (m,f),e in examples.items()],
        'scope':'Post-hoc diagnostic strata of the already-inspected frozen test; small subgroup intervals do not demonstrate broad generalization or causal mechanisms.'}
    (a.directory/'all_seven_mechanism_diagnostics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    for r in output:
        if r['axis']=='mechanism':print(r['model'],r['family'],r['value'],f"{r['before_correct']}->{r['after_correct']}/{r['questions']}")

if __name__=='__main__':main()
