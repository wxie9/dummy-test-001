#!/usr/bin/env python3
"""Score both members of a counterfactual pair, not only pooled accuracy."""
import json
import argparse
from pathlib import Path
from collections import defaultdict
from build_targeted_v5 import OUT
from summarize_targeted_v4 import paired, stats

def main():
    global OUT
    ap=argparse.ArgumentParser();ap.add_argument('--data-dir',type=Path,default=OUT);ap.add_argument('--run-version',choices=['v5','v5-3ep','v5-guard','v6','v6-3ep','v6-factmix','v7','v7-lr5','v8-steps'],default='v5')
    a=ap.parse_args();OUT=a.data_dir
    metadata={r['_meta']['id']:r['_meta'] for r in map(json.loads,(OUT/'development.jsonl').read_text().splitlines())}
    result={}
    for model in ('qwen3','qwen35'):
        run=OUT/'evidence/runs'/f'{model}-20261030-targeted-{a.run_version}'
        assert (run/'status.txt').read_text().strip()=='complete'
        before=json.loads((run/'development-before/rows.json').read_text())
        after=json.loads((run/'development-after/rows.json').read_text())
        pairs=paired(before,after)
        categories=defaultdict(list);groups=defaultdict(list);contexts=defaultdict(list)
        for r in pairs:
            m=metadata[r['id']];family=m['family']
            if family=='insufficient':sub=m.get('pair_role',m.get('facts',{}).get('variant','unspecified'))+('/'+r['question'] if a.run_version.startswith('v6') else '')
            elif family=='policy':sub=m.get('pair_kind',m['subtype'])+'/'+r['question']
            elif family in ('probability','multihop'):sub=m['subtype']+'/'+r['question']
            else:continue
            categories[family+'/'+sub].append(r)
            if family in ('insufficient','policy'):
                contexts[(family,r['id'])].append(r)
                if not a.run_version.startswith(('v7','v8')):groups[(family,m['group_id'])].append(r)
        group_stats=defaultdict(list)
        for (family,group),rs in groups.items():
            assert len({r['id'] for r in rs})==2
            m=metadata[rs[0]['id']]
            if family=='insufficient':
                kind='deciding' if any(metadata[r['id']]['pair_role']=='missing_deciding' for r in rs) else 'nondeciding'
            else:kind=m['pair_kind']
            group_stats[family+'/'+kind].append({'id':group,'before_ok':all(r['before_ok'] for r in rs),'after_ok':all(r['after_ok'] for r in rs)})
        context_stats=defaultdict(list)
        for (family,rid),rs in contexts.items():context_stats[family].append({'id':rid,'before_ok':all(r['before_ok'] for r in rs),'after_ok':all(r['after_ok'] for r in rs)})
        result[model]={'subquestion':{k:stats(v) for k,v in categories.items()},'whole_pair':{k:stats(v) for k,v in group_stats.items()},'whole_context':{k:stats(v) for k,v in context_stats.items()}}
    scope='Same-generator development. Whole-context success requires every question correct; v7 has no paired siblings.' if a.run_version.startswith(('v7','v8')) else 'Same-generator development. A whole pair is correct only if every subquestion in both siblings is correct.'
    (OUT/'development_pair_diagnostics.json').write_text(json.dumps({'models':result,'scope':scope},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({m:r['whole_pair'] for m,r in result.items()},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
