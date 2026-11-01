#!/usr/bin/env python3
"""Create benchmark-compatible development copies without changing task content.

The Kev benchmark reports accuracy only for records whose ``_meta.variant`` is
``clean``.  The synthetic development records retain provenance variants such
as ``error_neighborhood`` and ``independent_development``; those labels are
useful for lineage but make the benchmark's scored population empty.  This
script derives evaluation-only copies that change only that one metadata field.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def derive(model: str) -> dict[str, object]:
    source = ROOT / f"{model}_combined_development.jsonl"
    output = ROOT / f"{model}_eval_development.jsonl"
    records = 0
    original_variants: dict[str, int] = {}

    with source.open(encoding="utf-8") as reader, output.open("w", encoding="utf-8") as writer:
        for line in reader:
            record = json.loads(line)
            meta = record["_meta"]
            variant = meta.get("variant")
            original_variants[variant] = original_variants.get(variant, 0) + 1
            meta["variant"] = "clean"
            writer.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            records += 1

    return {
        "model": model,
        "source": source.name,
        "source_sha256": digest(source),
        "output": output.name,
        "output_sha256": digest(output),
        "records": records,
        "original_variants": original_variants,
        "changed_field": "_meta.variant",
        "new_value": "clean",
    }


def main() -> None:
    audit = {model: derive(model) for model in ("4b", "9b")}
    (ROOT / "eval_development_derivation.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
