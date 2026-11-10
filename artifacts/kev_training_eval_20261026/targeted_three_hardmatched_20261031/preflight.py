import json
import sys
from pathlib import Path
from kev.model import load_tokenizer, fits, training_context
from kev.data import load_records, materialize

base, revision, folder, output = sys.argv[1:]
tok = load_tokenizer(base, revision=revision)
result = {}
for name, expected in [("train", 720), ("development", 60)]:
    rows = load_records(str(Path(folder) / f"{name}.jsonl"))
    rejected = [r["_meta"]["id"] for r in rows if not fits(materialize(r), tok, **training_context(7552))]
    assert len(rows) == expected and not rejected
    result[name] = {
        "records": len(rows),
        "questions": sum(len(r["questions"]) for r in rows),
        "rejected": rejected,
    }
Path(output).write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result), flush=True)
