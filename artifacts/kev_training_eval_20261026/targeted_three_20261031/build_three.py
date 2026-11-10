#!/usr/bin/env python3
import hashlib
import json
from collections import Counter
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "targeted_v6_20261030" / "train.jsonl"
OUTPUT = Path(__file__).resolve().parent / "train.jsonl"
KEEP = {"temporal", "probability", "multihop"}

counts = Counter()
subquestions = Counter()
with SOURCE.open() as src, OUTPUT.open("w") as out:
    for line in src:
        row = json.loads(line)
        family = row["_meta"]["family"]
        if family not in KEEP:
            continue
        out.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        counts[family] += 1
        subquestions[family] += len(row["questions"])

payload = OUTPUT.read_bytes()
manifest = {
    "source": str(SOURCE),
    "selection": sorted(KEEP),
    "contexts": dict(sorted(counts.items())),
    "subquestions": dict(sorted(subquestions.items())),
    "total_contexts": sum(counts.values()),
    "total_subquestions": sum(subquestions.values()),
    "sha256": hashlib.sha256(payload).hexdigest(),
}
(OUTPUT.parent / "manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
)
print(json.dumps(manifest, ensure_ascii=False, indent=2))
