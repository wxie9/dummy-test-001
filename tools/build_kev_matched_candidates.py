#!/usr/bin/env python3
"""Visible-rule constructors for v9 matched views, without benchmark imports."""
import copy
import random
import re
from datetime import date, timedelta
from fractions import Fraction as F
from decimal import Decimal, ROUND_HALF_UP, localcontext
import build_kev_policy_transfer_candidates as policy
import build_kev_insufficient_transfer_candidates as insuff
import build_kev_probability_transfer_candidates as prob
import build_kev_multihop_transfer_candidates as multi
from build_kev_multihop_coverage_candidates import NAMES
from build_targeted_v4_components import record, choice
from check_targeted_v4_rules import gold, materialize

NONE='None of the listed candidates'

def cash(v):
    x=Decimal(v.numerator)/Decimal(v.denominator) if isinstance(v,F) else Decimal(v)
    return ('-' if x<0 else '')+'$'+format(abs(x).quantize(Decimal('.01'),rounding=ROUND_HALF_UP),'.2f')

def lock_questions(a,b,rng):
    """Same prompts/options/order; correct values from each visible-state solver."""
    assert a['questions'].keys()==b['questions'].keys()
    for qid,x in a['questions'].items():
        y=b['questions'][qid];assert x['type']==y['type'] and x['instructions']==y['instructions']
        if x['type']!='choice':assert x.get('criteria')==y.get('criteria');continue
        ga,gb=gold(a,qid),gold(b,qid)
        pool=list(dict.fromkeys([ga,gb]+list(x['criteria'].values())+list(y['criteria'].values())))
        if a['_meta']['family']=='policy' and qid=='amount' and '$0.00' not in pool:pool.append('$0.00')
        required=list(dict.fromkeys([ga,gb]));other=[v for v in pool if v not in required]
        # Preserve the salient zero/none distractor on both sides of a pair.
        for v in pool:
            if v in [NONE,'$0.00'] and v not in required:required.append(v)
        other=[v for v in other if v not in required];rng.shuffle(other)
        values=required+other[:max(0,5-len(required))];rng.shuffle(values);assert 3<=len(values)<=5
        criteria=dict(zip('abcde',values))
        for q,g in [(x,ga),(y,gb)]:
            q['criteria']=copy.deepcopy(criteria);q['label']=next(k for k,v in criteria.items() if v==g)
            q['target']={q['label']:1.0}
    assert all({k:v for k,v in a['questions'][q].items() if k not in ['label','target']}=={k:v for k,v in b['questions'][q].items() if k not in ['label','target']} for q in a['questions'])

def set_choice(r,qid,value):
    q=r['questions'][qid]
    if value not in q['criteria'].values():q['criteria']['new_correct']=value
    q['label']=next(k for k,v in q['criteria'].items() if v==value)
    q.pop('target',None)

def policy_pair(i,target,rng):
    # Domain kept balanced while cover count and operation order vary.
    a=policy.build(i%4+4*rng.randrange(1000),'pay_loss' if target=='legal_zero' else target,rng)
    factor=[1,5,10][i%3]
    a['state']=re.sub(r'\$(\d+)\.00',lambda m:cash(int(m[1])*factor),a['state'])
    if target=='legal_zero':
        event=re.search(r'\[Claim facts\]\nEvent: ([^.]+)',a['state'])[1]
        section=next(x for x in re.findall(r'\[Cover C\d+\] [^\n]+\n.*?(?=\n\n|\Z)',a['state'],re.S) if x.splitlines()[0].endswith(event))
        fee=int(re.search(r'One deductible: \$(\d+)\.00',section)[1])
        a['state']=re.sub(r'Approved loss: \$\d+\.00',f'Approved loss: {cash(rng.randint(0,fee))}',a['state'])
    # Rebuild gold after money scaling; old reason strings remain meaningful.
    def label(r):
        why,amount=policy.solve_visible(r['state']);set_choice(r,'reason',why);set_choice(r,'amount',cash(amount));return amount
    label(a);b=copy.deepcopy(a);s=b['state'];event=re.search(r'\[Claim facts\]\nEvent: ([^.]+)',s)[1]
    selected=next((code,body) for code,title,body in re.findall(r'\[Cover (C\d+)\] ([^\n]+)\n(.*?)(?=\n\n|\Z)',s,re.S) if title==event)
    code,body=selected;domain=re.search(r'POLICY DOMAIN: (\w+)',s)[1];d=policy.DOMAINS[domain]
    if i%5==0:
        other=next(x for x in re.findall(r'(C\d+) purchase status:',s) if x!=code)
        s=re.sub(other+r' purchase status: (included|not included)',lambda m:other+' purchase status: '+('not included' if m[1]=='included' else 'included'),s,count=1)
        mutation='unrelated_cover_purchase'
    elif i%5==1 and target in ['pay_limit','pay_sublimit']:
        old='Subtract one deductible from approved loss, flooring at zero, then cap the remainder by the applicable ceilings.'
        new='Cap approved loss by the applicable ceilings first, then subtract one deductible, flooring at zero.'
        s=s.replace(old,new) if old in s else s.replace(new,old);mutation='deductible_order'
    elif target=='legal_zero':
        fee=int(re.search(r'One deductible: \$(\d+)\.00',body)[1])
        s=re.sub(r'Approved loss: \$\d+\.00',f'Approved loss: {cash(fee+factor*7)}',s);mutation='loss_crosses_deductible'
    else:
        mutate=target if not target.startswith('pay_') else ['not_purchased','waiting','late','threshold','flag','intentional'][(i//5)%6]
        repair=not target.startswith('pay_')
        if mutate=='not_purchased':
            s=re.sub(code+r' purchase status: (included|not included)',code+' purchase status: '+('included' if repair else 'not included'),s,count=1)
        elif mutate=='waiting':
            start=date.fromisoformat(re.search(r'Inception date: ([\d-]+)',s)[1]);incident=date.fromisoformat(re.search(r'Incident date: ([\d-]+)',s)[1]);w=int(re.search(r'Waiting interval: (\d+)',body)[1])
            new=incident-timedelta(days=w if repair else w-1)
            s=s.replace('Inception date: '+str(start),'Inception date: '+str(new))
        elif mutate=='late':
            incident=date.fromisoformat(re.search(r'Incident date: ([\d-]+)',s)[1]);n=int(re.search(r'Notice interval: (\d+)',body)[1]);new=incident+timedelta(days=n if repair else n+1)
            s=re.sub(r'Report date: [\d-]+','Report date: '+str(new),s)
        elif mutate=='threshold':
            # Toggle the exception only when the exclusion actually triggers.
            field,op,n=re.search(r'Threshold exclusion: (.+?) (greater than|at most) (\d+)\.',body).groups();v=int(re.search('Measured '+re.escape(field)+r': (\d+)',s)[1]);trigger=v>int(n) if op=='greater than' else v<=int(n)
            if not trigger:
                # A positive case may have no triggered threshold; change the
                # field across its boundary only if no exception is accepted.
                if re.search(re.escape(d['exception'])+r': (accepted|not accepted)',s)[1]=='accepted':raise ValueError('No one-fact threshold flip')
                s=re.sub('Measured '+re.escape(field)+r': \d+','Measured '+field+': '+str(int(n)+1 if op=='greater than' else n),s)
            else:s=re.sub(re.escape(d['exception'])+r': (accepted|not accepted)',d['exception']+': '+('accepted' if repair else 'not accepted'),s)
        elif mutate=='flag':
            flag=re.search(re.escape(d['flag'])+r': (present|absent)',s)[1]
            if flag=='absent':s=s.replace(d['flag']+': absent',d['flag']+': present')
            else:s=re.sub(re.escape(d['waiver'])+r': (accepted|not accepted)',d['waiver']+': '+('accepted' if repair else 'not accepted'),s)
        else:s=re.sub(r'Intentional loss: (yes|no)','Intentional loss: '+('no' if repair else 'yes'),s)
        mutation='eligibility_'+mutate
    assert s!=a['state'];b['state']=s;label(b)
    for r in [a,b]:
        r['_meta']['facts']={'original_target':target,'domain':domain,'money_scale':factor,'mutation':mutation,'expected_payment':policy.solve_visible(r['state'])[1]}
    lock_questions(a,b,rng);policy.verify(a);policy.verify(b)
    return a,b,mutation

MISSING={
 'return':r'Delivery took place on [\d-]+\.',
 'approval':r'The actual signatory holds the rank [^.]+\.',
 'tenure':r'The company employment began on [\d-]+\.',
 'shipping':r'The merchandise discount is \$\d+\.',
 'overtime':r'Friday: \d+ hours?\.',
 'warranty':r'The confirmed cause is [^.]+\.',
 'price_match':r'The competitor item is (?:in stock|out of stock)\.'}

def insufficient_pair(scene,i,variant,rng):
    a=insuff.make(scene,i,variant,rng);a['state']=insuff.canonical_dates(multi.unwrap(a['state']))
    if scene=='price_match':
        factor=rng.randint(2,31)
        a['state']=re.sub(r'\$(\d+)',lambda m:'$'+str(int(m[1])*factor),a['state'])
        a['_meta']['facts']['money_scale']=factor
    b=copy.deepcopy(a);s=b['state']
    if variant in ['yes','no']:
        s,n=re.subn(MISSING[scene],'',s);assert n==1;mutation='remove_deciding_fact'
    else:
        lines=[line for line in s.splitlines() if not re.search(r'absent from this file|has not been supplied|is unavailable|is not stated|are not recorded|has not been determined|availability is unreported',line)]
        s='\n'.join(lines)
        take=lambda pat:re.search(pat,s)[1]
        bit=i%2
        if scene=='return':fact='Delivery took place on '+take(r'placed on ([\d-]+)' if bit else r'requested on ([\d-]+)')+'.'
        elif scene=='approval':fact='The actual signatory holds the rank '+insuff.RANKS[0 if bit else -1]+'.'
        elif scene=='tenure':
            app=date.fromisoformat(take(r'application date is ([\d-]+)'));move=date.fromisoformat(take(r'move took place on ([\d-]+)'));years=int(take(r'after (\d+) complete'))
            hire=move if bit else min(move,date(app.year-years-2,app.month,app.day));fact='The company employment began on '+str(hire)+'.'
        elif scene=='shipping':fact='The merchandise discount is $'+(take(r'from \$0 through \$(\d+)') if bit else '0')+'.'
        elif scene=='overtime':fact='Friday: '+(take(r'between 0 and (\d+)') if bit else '0')+' hours.'
        elif scene=='warranty':fact='The confirmed cause is '+('accidental damage' if bit else 'production defect')+'.'
        else:fact='The competitor item is '+('out of stock' if bit else 'in stock')+'.'
        s+='\n'+fact;mutation='complete_missing_fact'
    b['state']=s
    for r in [a,b]:
        outcomes=insuff.solve(r['state']);answer=next(iter(outcomes)) if len(outcomes)==1 else insuff.UNKNOWN
        set_choice(r,'decision',answer)
        r['_meta']['facts'].update(parent_variant=variant,possible_outcomes=sorted(outcomes),
                                  variant='unknown' if len(outcomes)>1 else 'yes' if answer==insuff.ACTIONS[scene][0] else 'no' if answer==insuff.ACTIONS[scene][1] else 'keep_price')
    lock_questions(a,b,rng);insuff.verify(a);insuff.verify(b)
    return a,b,mutation

def dependency_pair(i,rng,split):
    depth=[2,3,4,5][i%4];names=rng.sample(NAMES,14)
    # Alternate simple identifiers and compound service identifiers.
    if (i//4)%2:names=[x.lower()+'_'+rng.choice(['worker','router','service']) for x in names]
    chain=names[:depth+1];down=chain[0];target=chain[-1];noise=names[7:]
    edges=[(b,a,True) for a,b in zip(chain,chain[1:])]
    edges += [(down,noise[0],True),(noise[1],noise[2],True),(noise[3],down,False),(noise[4],noise[3],True)]
    # Fresh held-out branch-count combination, rather than crossing matched views.
    if split=='development':edges += [(noise[5],chain[1],True),(noise[6],noise[5],True)]
    candidates=[target,noise[0],noise[1],noise[4],NONE]
    critical=rng.randrange(depth);start_blocked=bool((i//4)%2);invariant=i%5==0
    variants=[];order=list(range(len(edges)));rng.shuffle(order)
    for j in range(2):
        es=copy.deepcopy(edges);blocked=start_blocked if invariant else start_blocked ^ bool(j)
        if blocked:a,b,_=es[critical];es[critical]=(a,b,False)
        if invariant and j:
            # Change only an unrelated hard/soft edge; no candidate reaches it.
            a,b,_=es[depth+1];es[depth+1]=(a,b,False)
        lines=[f'{es[k][0]} requires {es[k][1]} through a {"hard" if es[k][2] else "soft"} dependency.' for k in order]
        state='FAILURE RULE\nA failed hard prerequisite disables its consumer. Apply this rule repeatedly until no further units fail. Soft links never propagate failure. Failure never propagates from a consumer to its prerequisite. All dependencies are listed.\n'+'\n'.join(lines)+f'\nInitial failed unit: {down}. All other units initially function.'
        q=choice(rng,'After propagation, which listed candidate has failed?',NONE if blocked else target,candidates)
        r=record('multihop',i,state,{'decision':q},{'queried_distance_if_hard':depth,'blocked':blocked,'critical_edge_position':critical,'extra_side_branches':2 if split=='development' else 0},'dependency_candidates','Compute failure closure from visible hard edges; soft links block propagation.')
        variants.append(r)
    a,b=variants;lock_questions(a,b,rng);multi.verify(a);multi.verify(b)
    return a,b,'unrelated_edge' if invariant else 'critical_hard_soft_edge'

def probability_answers(r):
    s=r['state'];kind=r['_meta']['subtype'];answers={}
    if kind=='table':
        matrix=prob.read_table(s)
        for qid,q in r['questions'].items():
            if qid=='forward':row,col=re.search(r'Among records from (.+), what percentage have status (.+)\?',q['instructions']).groups();p=F(matrix[row][col],sum(matrix[row].values()))
            else:col,row=re.search(r'Among records with status (.+), what percentage come from (.+)\?',q['instructions']).groups();p=F(matrix[row][col],sum(v[col] for v in matrix.values()))
            answers[qid]=prob.percent(p)
        return answers
    if kind=='bayes':
        base,hit,false=map(int,re.findall(r'(\d+)%',s));p=F(base*hit,base*hit+(100-base)*false);answers['posterior']=prob.percent(p);answers['more_likely']=p>F(1,2)
    elif kind in ['all','any','any_fail']:
        rates=[F(v)/100 for v in re.findall(r'(\d+)%',s)];product=F(1);none=F(1)
        for v in rates:product*=v;none*=1-v
        p={'all':product,'any_fail':1-product,'any':1-none}[kind];answers['probability']=prob.percent(p)
    elif kind=='compare':
        x,y,z=[F(v)/100 for v in re.findall(r'([\d.]+)%',s)];p=x*y if 'both A and B happen' in s else x+y-x*y
        return {'decision':'X is more likely' if p>z else 'Y is more likely' if p<z else 'They have equal probabilities'}
    else:
        values={}
        for name,cost,rest in re.findall(r'(\w+): upfront cost \$([\d.]+); ([^\n]+)',s):
            terms=re.findall(r'(\d+)%: (gain|lose) \$([\d]+\.\d{2})',rest);assert sum(int(t[0]) for t in terms)==100
            values[name]=sum(F(w)*F(v)/100*(1 if op=='gain' else -1) for w,op,v in terms)-F(cost)
        best=max(values,key=values.get);assert sum(v==values[best] for v in values.values())==1
        asked=re.search(r'cash flow of (\w+)',r['questions']['value']['instructions'])[1]
        return {'project':best,'value':cash(values[asked])}
    if 'bucket' in r['questions']:
        bins=r['questions']['bucket']['criteria']
        answers['bucket']=next(i for i,t in enumerate(bins) if (lambda lo,hi:lo<=p*100<hi or hi==100 and p==1)(*map(int,re.findall(r'(\d+)%',t))))
    return answers

def verify_probability(r):
    """Separate Decimal solver; generation above uses exact Fraction arithmetic.

    The legacy checker uses binary-float formatting at half-cent boundaries.
    New questions explicitly specify round-half-up, so verify that convention.
    """
    kind=r['_meta']['subtype'];s=r['state'];expected={}
    if kind!='table':s=prob.decode(s,r['_meta']['rate_style'])
    with localcontext() as ctx:
        ctx.prec=60
        pct=lambda x:format((x*100).quantize(Decimal('.01'),rounding=ROUND_HALF_UP),'.2f')+'%'
        if kind=='table':
            matrix=prob.read_table(s)
            for qid,q in r['questions'].items():
                if qid=='forward':
                    row,col=re.search(r'Among records from (.+), what percentage have status (.+)\?',q['instructions']).groups();den=sum(matrix[row].values())
                else:
                    col,row=re.search(r'Among records with status (.+), what percentage come from (.+)\?',q['instructions']).groups();den=sum(v[col] for v in matrix.values())
                expected[qid]=pct(Decimal(matrix[row][col])/den)
        elif kind=='bayes':
            base,hit,false=map(Decimal,re.findall(r'(\d+)%',s));positive=base*hit;value=positive/(positive+(100-base)*false)
            expected['posterior']=pct(value);expected['more_likely']=value>Decimal('.5')
        elif kind in ['all','any','any_fail']:
            rates=[Decimal(v)/100 for v in re.findall(r'(\d+)%',s)];all_success=Decimal(1);all_fail=Decimal(1)
            for v in rates:all_success*=v;all_fail*=1-v
            value=all_success if kind=='all' else 1-all_success if kind=='any_fail' else 1-all_fail
            expected['probability']=pct(value)
        elif kind=='compare':
            x,y,z=[Decimal(v)/100 for v in re.findall(r'([\d.]+)%',s)]
            value=x*y if 'both A and B happen' in s else 1-(1-x)*(1-y)
            expected['decision']='X is more likely' if value>z else 'Y is more likely' if value<z else 'They have equal probabilities'
        else:
            values={}
            for name,cost,terms in re.findall(r'(\w+): upfront cost \$([\d.]+); ([^\n]+)',s):
                outcomes=re.findall(r'(\d+)%: (gain|lose) \$([\d]+\.\d{2})',terms);assert sum(int(x[0]) for x in outcomes)==100
                values[name]=sum(Decimal(w)*Decimal(v)/100*(1 if op=='gain' else -1) for w,op,v in outcomes)-Decimal(cost)
            maximum=max(values.values());winners=[k for k,v in values.items() if v==maximum];assert len(winners)==1
            name=re.search(r'cash flow of (\w+)',r['questions']['value']['instructions'])[1];amount=values[name]
            expected={'project':winners[0],'value':('-' if amount<0 else '')+'$'+format(abs(amount).quantize(Decimal('.01'),rounding=ROUND_HALF_UP),'.2f')}
        if 'bucket' in r['questions']:
            matching=[]
            for i,interval in enumerate(r['questions']['bucket']['criteria']):
                lo,hi=map(Decimal,re.findall(r'(\d+)%',interval))
                if lo<=value*100<hi or hi==100 and value==1:matching.append(i)
            assert len(matching)==1;expected['bucket']=matching[0]
        assert set(expected)==set(r['questions'])
        for qid,value in expected.items():
            q=r['questions'][qid];actual=gold(r,qid) if q['type']=='choice' else q['label']
            assert actual==value,(r['_meta']['id'],qid,actual,value)
    materialize(r)

def probability_pair(i,kind,rng):
    a=prob.table(i,rng) if kind=='table' else prob.make(i,kind,rng)
    if a is None:raise ValueError('Degenerate initial draw')
    b=copy.deepcopy(a);invariant=i%5==0
    if kind=='table':
        matrix=prob.read_table(a['state']);keys=list(matrix);cols=list(matrix[keys[0]])
        if invariant:
            matrix={k:{c:v*3 for c,v in vs.items()} for k,vs in matrix.items()};mutation='all_counts_scaled'
        else:
            row=rng.choice(keys);col=rng.choice(cols);matrix[row][col]+=rng.randint(1,25)*[1,10,100,1000,10000][i%5];mutation='one_cell_count'
        def render(mat,original):
            if isinstance(original,dict):
                s=copy.deepcopy(original)
                for rec in s['records']:rec['counts']=[mat[rec['group']][c] for c in s['status_order']]
                return s
            first=original.splitlines()[0]
            if '| Group |' in original:return first+'\n| Group | '+' | '.join(cols)+' |\n'+'\n'.join('| '+k+' | '+' | '.join(str(mat[k][c]) for c in cols)+' |' for k in keys)
            return first+'\n'+'\n'.join(k+': '+'; '.join(str(mat[k][c])+' '+c for c in cols)+'.' for k in keys)
        b['state']=render(matrix,a['state'])
    elif kind in ['bayes','all','any','any_fail']:
        if invariant and kind!='bayes':
            values=re.findall(r'\d+%',a['state']);reordered=values[1:]+values[:1];it=iter(reordered);b['state']=re.sub(r'\d+%',lambda m:next(it),a['state']);mutation='independent_event_order'
        elif invariant:
            b['state']=a['state']+' The case identifiers have been renamed; the population and all stated rates are unchanged.';mutation='irrelevant_identifier_notice'
        else:
            values=list(re.finditer(r'\d+%',a['state']));j=0 if kind=='bayes' else rng.randrange(len(values));m=values[j];value=rng.choice([v for v in [1,5,15,35,55,75,95,99] if v!=int(m[0][:-1])]);b['state']=a['state'][:m.start()]+str(value)+'%'+a['state'][m.end():];mutation='one_rate'
    elif kind=='compare':
        values=list(re.finditer(r'[\d.]+%',a['state']))
        if invariant:
            replacements=[values[1][0],values[0][0],values[2][0]];it=iter(replacements);b['state']=re.sub(r'[\d.]+%',lambda m:next(it),a['state']);mutation='symmetric_event_order'
        else:
            x,y=[F(v[0][:-1])/100 for v in values[:2]];p=x*y if 'both A and B happen' in a['state'] else x+y-x*y
            old=F(values[-1][0][:-1])/100
            target=max(F(0),p-F(1,100)) if old>=p else min(F(1),p+F(1,100));m=values[-1];b['state']=a['state'][:m.start()]+prob.percent(target)+a['state'][m.end():];mutation='comparison_reference_rate'
    else:
        if invariant:
            lines=a['state'].splitlines();b['state']='\n'.join([lines[0]]+lines[2:]+[lines[1]]);mutation='project_order'
        else:
            asked=re.search(r'cash flow of (\w+)',a['questions']['value']['instructions'])[1]
            b['state']=re.sub(re.escape(asked)+r': upfront cost \$([\d.]+)',lambda m:asked+': upfront cost '+cash(F(m[1])+rng.randint(1,20)*25),a['state']);mutation='one_upfront_cost'
    if a['state']==b['state']:raise ValueError('Unchanged proposed view')
    for r in [a,b]:
        for qid,value in probability_answers(r).items():
            if r['questions'][qid]['type']=='choice':set_choice(r,qid,value)
            else:r['questions'][qid]['label']=value
        for qid,q in r['questions'].items():
            if qid in ['forward','reverse','posterior','probability','value'] and 'half up' not in q['instructions'].lower():
                q['instructions']+=' Use round-half-up for two decimal places.'
        if kind=='table':
            mat=prob.read_table(r['state']);f=r['_meta']['facts']
            f['counts']=[[mat[row][col] for col in f['status_labels']] for row in f['row_labels']]
        elif kind=='bayes':
            base,hit,false=map(int,re.findall(r'(\d+)%',r['state']));r['_meta']['facts']={'prevalence':base,'sensitivity':hit,'false_positive':false}
        elif kind in ['all','any','any_fail']:
            r['_meta']['facts']={'probabilities':list(map(int,re.findall(r'(\d+)%',r['state'])))}
        else:r['_meta']['facts']={'mutation':mutation,'answers_from_visible_text':probability_answers(r)}
    lock_questions(a,b,rng)
    if kind!='table':
        style=['percent','words','fraction','outof'][(i//5)%4]
        for r in [a,b]:r['state']=prob.express(r['state'],style);r['_meta']['rate_style']=style
    for r in [a,b]:verify_probability(r)
    return a,b,mutation
