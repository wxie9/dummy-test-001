#!/usr/bin/env python3
"""New 350-context component: table targets/ordering and rate expressions.

No benchmark generator or label is imported. This is not the full 1500 corpus.
All labels are checked from visible text, including decoding displayed rates.
"""
import copy
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction as F
from pathlib import Path
from build_kev_probability_coverage_candidate import make, verify as old_verify, COUNTS
from build_targeted_v4_components import ROOT, choice, record
from build_targeted_v5 import digest
from check_targeted_v4_rules import materialize, gold

OUT=ROOT/'artifacts/kev_training_eval_20261026/probability_transfer_candidates_20261030'
VERSION='probability-transfer-candidate-20261030'
SMALL='zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split()
TENS='zero ten twenty thirty forty fifty sixty seventy eighty ninety'.split()
WORDS={w:i for i,w in enumerate(SMALL)}|{w:i*10 for i,w in enumerate(TENS) if i>=2}
RATE_WORDS='(?:'+'|'.join(sorted(set(WORDS)|{'hundred','point'},key=len,reverse=True))+')'
WORD_RATE=re.compile(r'\b('+RATE_WORDS+r'(?:[ -]'+RATE_WORDS+r')*) percent\b')
PAIRS=[('North depot','South depot','returned','kept'),('Supplier R','Supplier S','defective','acceptable'),
       ('Morning shift','Evening shift','late','on time'),('Coastal branch','Inland branch','renewed','not renewed')]

def number_words(n):
    if n==100:return 'one hundred'
    if n<20:return SMALL[n]
    return TENS[n//10]+('-'+SMALL[n%10] if n%10 else '')

def decimal_text(n):return format(Decimal(n),'f').rstrip('0').rstrip('.') if '.' in format(Decimal(n),'f') else format(Decimal(n),'f')

def to_words(s):
    s=decimal_text(s);parts=s.split('.')
    return number_words(int(parts[0]))+(' point '+' '.join(SMALL[int(c)] for c in parts[1]) if len(parts)>1 else '')

def from_words(s):
    parts=s.replace('-',' ').split(' point ');n=0
    for w in parts[0].split():
        if w=='hundred':n*=100
        else:n+=WORDS[w]
    if len(parts)==1:return str(n)
    decimals=[WORDS[w] for w in parts[1].split()];assert all(0<=d<=9 for d in decimals)
    return str(n)+'.'+''.join(map(str,decimals))

def rate_expression(s,style):
    if style=='percent':return s+'%'
    if style=='words':return to_words(s)+' percent'
    f=F(s)/100
    if style=='fraction':return f'{f.numerator}/{f.denominator}'
    return f'{f.numerator} out of every {f.denominator}'

def express(s,style):
    s=re.sub(r'(\d+(?:\.\d+)?)%',lambda m:rate_expression(m[1],style),s)
    if style=='outof':s=re.sub(r'(\d+ out of every \d+) of cases',r'\1 cases',s)
    return s

def pct_number(p):
    # Inputs are finite decimal probabilities; Fraction arithmetic preserves them.
    n=Decimal(p.numerator)*100/Decimal(p.denominator)
    return decimal_text(n)

def decode(s,style):
    if style=='words':s=WORD_RATE.sub(lambda m:from_words(m[1])+'%',s)
    if style=='fraction':s=re.sub(r'\b(\d+)/(\d+)\b',lambda m:pct_number(F(int(m[1]),int(m[2])))+'%',s)
    if style=='outof':
        s=re.sub(r'\b(\d+) out of every (\d+)\b',lambda m:pct_number(F(int(m[1]),int(m[2])))+'%',s)
        s=re.sub(r'(In [^.]+, \d+(?:\.\d+)?%) cases are',r'\1 of cases are',s)
    return s

def normalize_percent_precision(s):
    return re.sub(r'(\d+(?:\.\d+)?)%',lambda m:decimal_text(m[1])+'%',s)

def percent(p):
    return str((Decimal(p.numerator)*100/Decimal(p.denominator)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))+'%'

def numeric_question(rng,prompt,p,alternatives):
    answer=percent(p)
    extra=[F(0),F(1),F(1,4),F(1,2),F(3,4),max(F(0),p-F(7,100)),min(F(1),p+F(11,100))]
    wrong=list(dict.fromkeys(percent(x) for x in alternatives+extra if percent(x)!=answer))
    # Preserve the opposite conditioning as a diagnostic distractor.
    required=wrong[0];others=wrong[1:];rng.shuffle(others)
    q=choice(rng,prompt+' Round half up to two decimal places.',answer,[required]+others[:3]);assert len(q['criteria'])==5
    return q

def table(i,rng):
    first,second,yes,no=rng.choice(PAIRS);names=[first,second];statuses=[yes,no]
    scale=[1,10,100,1000,10000][i%5];counts=[[rng.randint(10,390)*scale for _ in range(2)] for _ in range(2)]
    ri=i%2;ci=(i//2)%2;row=names[ri];col=statuses[ci]
    row_order=[ri,1-ri] if (i//4)%2==0 else [1-ri,ri]
    col_order=[ci,1-ci] if (i//8)%2==0 else [1-ci,ci]
    layout=['prose','table','object'][i%3]
    scope='This is the complete audit. Each record belongs to exactly one group and one status; no record is counted twice.'
    if layout=='table':
        s=scope+'\n| Group | '+' | '.join(statuses[c] for c in col_order)+' |\n'
        s+='\n'.join('| '+names[r]+' | '+' | '.join(str(counts[r][c]) for c in col_order)+' |' for r in row_order)
    elif layout=='prose':
        s=scope+'\n'+'\n'.join(names[r]+': '+'; '.join(str(counts[r][c])+' '+statuses[c] for c in col_order)+'.' for r in row_order)
    else:
        s={'audit_scope':scope,'status_order':[statuses[c] for c in col_order],
           'records':[{'group':names[r],'counts':[counts[r][c] for c in col_order]} for r in row_order]}
    a=counts[ri][ci];forward=F(a,sum(counts[ri]));reverse=F(a,sum(counts[r][ci] for r in range(2)));total=sum(map(sum,counts))
    if percent(forward)==percent(reverse):return None
    wrong=[forward,reverse,F(a,total),1-forward,1-reverse,F(sum(counts[ri]),total),F(sum(counts[r][ci] for r in range(2)),total)]
    qs={'forward':numeric_question(rng,f'Among records from {row}, what percentage have status {col}?',forward,wrong),
        'reverse':numeric_question(rng,f'Among records with status {col}, what percentage come from {row}?',reverse,wrong)}
    return record('probability',i,s,qs,{'row_labels':names,'status_labels':statuses,'counts':counts,'target_row':row,'target_status':col,
        'target_row_position':row_order.index(ri),'target_status_position':col_order.index(ci),'layout':layout,'scale':scale},'table','Condition on the named set; row and column totals differ.')

def read_table(s):
    result={}
    if isinstance(s,dict):
        assert set(s)=={'audit_scope','status_order','records'}
        assert len(s['status_order'])==2 and len(set(s['status_order']))==2
        for r in s['records']:
            assert r['group'] not in result and len(r['counts'])==2
            result[r['group']]=dict(zip(s['status_order'],r['counts']))
    elif '| Group |' in s:
        lines=[line for line in s.splitlines() if line.startswith('|')];cols=[x.strip() for x in lines[0].split('|')[2:-1]]
        assert len(cols)==2
        for line in lines[1:]:
            cells=[x.strip() for x in line.split('|')[1:-1]];assert len(cells)==3
            result[cells[0]]=dict(zip(cols,map(int,cells[1:])))
    else:
        for line in s.splitlines()[1:]:
            m=re.fullmatch(r'(.+): (\d+) (.+); (\d+) (.+)\.',line);assert m,line
            result[m[1]]={m[3]:int(m[2]),m[5]:int(m[4])}
    assert len(result)==2 and all(len(v)==2 for v in result.values())
    assert len({tuple(sorted(v)) for v in result.values()})==1
    assert all(isinstance(n,int) and n>0 for row in result.values() for n in row.values())
    return result

def verify(r):
    if r['_meta']['subtype']=='table':
        matrix=read_table(r['state'])
        facts=r['_meta']['facts']
        assert list(matrix).index(facts['target_row'])==facts['target_row_position']
        assert list(next(iter(matrix.values()))).index(facts['target_status'])==facts['target_status_position']
        for qid,q in r['questions'].items():
            if qid=='forward':
                row,col=re.search(r'Among records from (.+), what percentage have status (.+)\?',q['instructions']).groups()
                expected=F(matrix[row][col],sum(matrix[row].values()))
            else:
                col,row=re.search(r'Among records with status (.+), what percentage come from (.+)\?',q['instructions']).groups()
                expected=F(matrix[row][col],sum(counts[col] for counts in matrix.values()))
            assert gold(r,qid)==percent(expected)
    else:
        canonical=copy.deepcopy(r);style=r['_meta']['rate_style'];s=r['state']
        if isinstance(s,dict):assert set(s)=={'topic','details'};s=s['details']
        canonical['state']=decode(s,style);old_verify(canonical)
    materialize(r)

def main():
    OUT.mkdir(exist_ok=True);seen=set()
    for p in (ROOT/'third_party/kev-source-20261025/evals').glob('*/test.jsonl'):
        seen.update(digest(r['state']) for r in map(json.loads,p.read_text().splitlines()))
    frozen=set(seen)
    previous=ROOT/'artifacts/kev_training_eval_20261026/targeted_v6_20261030/train.jsonl'
    seen.update(digest(r['state']) for r in map(json.loads,previous.read_text().splitlines()))
    manifest={'status':'component_only_not_trained','contexts_planned':350,'purpose':'Broaden target selection, ordering, representation and rate-language coverage; not the final 1500 corpus.','files':{}}
    for split,counts in COUNTS.items():
        rows=[];stats=defaultdict(Counter);mutations=0
        for kind,n in counts.items():
            for i in range(n):
                for attempt in range(10000):
                    rng=random.Random(f'{VERSION}/{split}/{kind}/{i}/{attempt}')
                    r=table(i,rng) if kind=='table' else make(i,kind,rng)
                    if r is None:continue
                    if kind!='table':
                        original_state=r['state']
                        style=['percent','words','fraction','outof'][i%4];r['state']=express(r['state'],style);r['_meta']['rate_style']=style
                        assert normalize_percent_precision(decode(r['state'],style))==normalize_percent_precision(original_state)
                        if (i//4)%2:r['state']={'topic':'Decision from the stated audit figures','details':r['state']}
                    h=digest(r['state'])
                    if h not in seen:break
                else:raise AssertionError('Could not generate unique case')
                seen.add(h);m=r['_meta'];m.update(id=f'{VERSION}/{split}/{kind}/{i}',group_id=f'{VERSION}/{split}/{kind}/{i}',source=VERSION,split=split,text_sha256=h)
                for q in r['questions'].values():q['src']=VERSION
                verify(r)
                for name,q in r['questions'].items():
                    wrong=[not q['label']] if q['type']=='noul' else [x for x in (range(len(q['criteria'])) if q['type']=='score' else q['criteria']) if x!=q['label']]
                    for label in wrong:
                        bad=copy.deepcopy(r);bad['questions'][name]['label']=label
                        try:verify(bad)
                        except AssertionError:mutations+=1
                        else:raise AssertionError(('Incorrect label accepted',m['id'],name,label))
                if kind=='table':
                    for axis in ['target_row_position','target_status_position','layout']:stats[axis][m['facts'][axis]]+=1
                else:stats['rate_style'][m['rate_style']]+=1
                rows.append(r)
        random.Random(VERSION+split).shuffle(rows);path=OUT/(split+'.candidate.jsonl');path.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows))
        for line in path.read_text().splitlines():verify(json.loads(line))
        manifest['files'][split]={'contexts':len(rows),'questions':sum(len(r['questions']) for r in rows),'coverage':{k:dict(v) for k,v in stats.items()},'incorrect_labels_rejected':mutations,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        (OUT/(split+'.examples.json')).write_text(json.dumps([next(r for r in rows if r['_meta']['subtype']==kind) for kind in counts],ensure_ascii=False,indent=2)+'\n')
    manifest['checks']={'normalized_state_train_dev_overlap':0,'normalized_state_frozen_test_overlap':0,'normalized_state_previous_v6_train_overlap':0,'visible_numeric_label_verification':True,'all_rate_representations_exactly_reconstruct_original_facts':True}
    manifest['limitations']=['Authored templates and same-author verifier, not external semantic review.','Test cases were inspected for coverage diagnosis; future results are not blind generalization.','Only the probability component is prepared; no new training has started.']
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps(manifest,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
