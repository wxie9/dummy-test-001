#!/usr/bin/env python3
"""Merge disjoint DecisionPivot runner shards and verify their item hashes."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("shard_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    copied: set[str] = set()

    for shard in sorted(path for path in args.shard_root.iterdir() if path.is_dir()):
        index_path = shard / "_items.json"
        if not index_path.is_file():
            raise FileNotFoundError(index_path)
        shard_hashes = json.loads(index_path.read_text(encoding="utf-8"))
        for task, digest in shard_hashes.items():
            if task in hashes and hashes[task] != digest:
                raise ValueError(f"conflicting item hash for {task}: {hashes[task]} vs {digest}")
            hashes[task] = digest

        for source in sorted(shard.glob("*.jsonl")):
            if source.name in copied:
                raise ValueError(f"duplicate task output: {source.name}")
            shutil.copy2(source, args.output / source.name)
            copied.add(source.name)

    if len(copied) != 13 or len(hashes) != 13:
        raise ValueError(f"expected 13 task outputs and hashes, got {len(copied)} outputs and {len(hashes)} hashes")

    (args.output / "_items.json").write_text(
        json.dumps(hashes, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"tasks": len(copied), "hashes": len(hashes), "output": str(args.output)}))


if __name__ == "__main__":
    main()
