#!/usr/bin/env python3
"""CPU-only comparison of trained adapter/head tensors to original stage3."""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
import torch
from safetensors.torch import load_file

def compare(before,after):
    assert list(sorted(before))==list(sorted(after))
    rows=[]
    for key in sorted(before):
        x,y=before[key],after[key]
        assert x.shape==y.shape
        assert torch.isfinite(x).all() and torch.isfinite(y).all()
        xf,yf=x.double(),y.double();d=yf-xf
        rows.append({'tensor':key,'dtype_before':str(x.dtype),'dtype_after':str(y.dtype),
          'elements':x.numel(),'changed_elements':int((x!=y).sum()),
          'before_l2_squared':float(xf.square().sum()),'delta_l2_squared':float(d.square().sum()),
          'max_abs_delta':float(d.abs().max())})
    n=sum(r['elements'] for r in rows);changed=sum(r['changed_elements'] for r in rows)
    base=sum(r['before_l2_squared'] for r in rows);delta=sum(r['delta_l2_squared'] for r in rows)
    return {'tensors':len(rows),'elements':n,'changed_tensors':sum(r['changed_elements']>0 for r in rows),
            'changed_elements':changed,'changed_element_pct':100*changed/n,
            'relative_l2_delta':(delta/base)**.5 if base else None,'all_finite':True,'by_tensor':rows}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);ap.add_argument('--version',default='v6');ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    torch.set_num_threads(2)
    out={'version':a.version,'models':{},'files':{},'scope':'Completed checkpoint tensor changes only. Does not inspect live process gradients, prove useful learning, or establish why accuracy changed.'}
    for model,original in [('qwen3','qwen3-06b-20261026'),('qwen35','replica-20261026')]:
        old=a.root/'runs'/original/'stage3';new=a.root/'runs'/(model+'-20261030-targeted-'+a.version)/'stage4'
        assert (new.parent/'status.txt').read_text().strip()=='complete'
        results={}
        for kind,filename in [('adapter','adapter_model.safetensors'),('head','head.pt')]:
            paths=[old/filename,new/filename]
            for p in paths:out['files'][str(p.relative_to(a.root))]=hashlib.sha256(p.read_bytes()).hexdigest()
            arrays=[load_file(str(p),device='cpu') if kind=='adapter' else torch.load(p,map_location='cpu',weights_only=True)['head'] for p in paths]
            results[kind]=compare(*arrays)
        out['models'][model]=results
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({m:{k:{s:v for s,v in r.items() if s!='by_tensor'} for k,r in d.items()} for m,d in out['models'].items()}))

if __name__=='__main__':main()
