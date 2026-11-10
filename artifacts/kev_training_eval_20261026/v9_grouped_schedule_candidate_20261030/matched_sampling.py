"""Keep explicitly declared matched views in one ordinary microbatch.

Uses record IDs only, never labels or evaluated outcomes. No rows are repeated.
The objective remains the existing per-question CE; this changes scheduling.
"""
import json
from collections import Counter


def load_pair_membership(path, requests):
    if not path:return {}
    with open(path,encoding='utf-8') as f:pairs=json.load(f)['train']
    counts=Counter(r['_meta']['id'] for r in requests)
    membership={}
    for pair in pairs:
        a,b=pair['base_id'],pair['matched_id']
        assert a!=b and counts[a]==counts[b]==1
        assert a not in membership and b not in membership
        membership[a]=membership[b]=pair['group_id']
    assert len(set(membership.values()))==len(pairs)
    return membership


def shuffle_matched_requests(requests, membership, rng, batch):
    assert batch>=2 and batch%2==0
    original=Counter(map(id,requests));units=[];grouped={}
    for r in requests:
        group=membership.get(r['_meta']['id'])
        if group is None:units.append([r])
        else:grouped.setdefault(group,[]).append(r)
    for records in grouped.values():
        assert len(records)==2
        rng.shuffle(records)
        units.append(records)
    rng.shuffle(units)
    used=0
    for i,unit in enumerate(units):
        available=batch-used
        if len(unit)>available:
            # A pair cannot fill one remaining slot; move a singleton here.
            j=next((j for j in range(i+1,len(units)) if len(units[j])<=available),None)
            if j is None:raise ValueError('Cannot pack matched units without changing record count')
            units[i],units[j]=units[j],units[i]
        used=(used+len(units[i]))%batch
    requests[:]=[r for unit in units for r in unit]
    assert Counter(map(id,requests))==original
    positions={r['_meta']['id']:i for i,r in enumerate(requests) if r['_meta']['id'] in membership}
    batches={}
    for rid,group in membership.items():batches.setdefault(group,set()).add(positions[rid]//batch)
    assert all(len(v)==1 for v in batches.values())
