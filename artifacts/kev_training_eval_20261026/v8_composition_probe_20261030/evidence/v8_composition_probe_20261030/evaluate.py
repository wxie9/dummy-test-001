import json,sys,hashlib,time
from pathlib import Path
from kev.data import load_records
from kev.model import training_context
from kev.predictors import LocalPredictor
from kev.checkpoint import LoadOptions
from kev.benchmark import evaluate_records
run,data,out=sys.argv[1:]
predictor=LocalPredictor(run,'cuda',LoadOptions.from_env(),context={**training_context(7552),'truncate':False})
start=time.time()
report,_=evaluate_records(load_records(data),predictor,out,heldout_sources=(),skip_overlong=False)
report.update(run=run,data=data,data_sha256=hashlib.sha256(Path(data).read_bytes()).hexdigest(),elapsed_seconds=time.time()-start,scope='Diagnostic labeled inputs; identify scope by data path/hash. Training inputs are in-sample and development shares generators.')
Path(out,'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'clean':report['clean'],'coverage':report['coverage']}),flush=True)
