#!/usr/bin/env python3
import json
import sys
from pathlib import Path

from kev.data import load_records, materialize
from kev.model import fits, load_tokenizer, training_context


base, revision, folder, model, output = sys.argv[1:]
expected = {
    "4b": {"train": 3084, "development": 538},
    "9b": {"train": 2928, "development": 486},
}[model]
tokenizer = load_tokenizer(base, revision=revision)
result = {"model": model, "base": base, "revision": revision, "max_state": 7552, "splits": {}}
for split, count in expected.items():
    path = Path(folder) / f"{model}_combined_{split}.jsonl"
    rows = load_records(str(path))
    rejected = []
    for row in rows:
        if not fits(materialize(row), tokenizer, **training_context(7552)):
            rejected.append({"id": row["_meta"]["id"], "family": row["_meta"].get("family")})
    result["splits"][split] = {
        "records": len(rows),
        "questions": sum(len(row["questions"]) for row in rows),
        "rejected": rejected,
    }
    if len(rows) != count:
        result["splits"][split]["expected_records"] = count
Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(result, ensure_ascii=False), flush=True)
assert all(result["splits"][name]["records"] == count for name, count in expected.items())
assert not any(result["splits"][name]["rejected"] for name in expected)
