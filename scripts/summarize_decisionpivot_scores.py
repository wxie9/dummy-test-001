#!/usr/bin/env python3
"""Extract headline and per-family DecisionPivot metrics from scores.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scores", type=Path)
    parser.add_argument("--system")
    args = parser.parse_args()

    payload = json.loads(args.scores.read_text(encoding="utf-8"))
    if "systems" in payload:
        system = args.system or next(iter(payload["systems"]))
        system_payload = payload["systems"][system]
        rows = list(system_payload["tasks"].values())
        layer_rows: dict[str, list[float]] = {}
        for row in rows:
            layer_rows.setdefault(row["layer"], []).append(float(row["score"]))
        layers = {
            layer: sum(values) / len(values) for layer, values in sorted(layer_rows.items())
        }
    else:
        system = args.system or next(
            key for key, value in payload.items() if "::" not in key and isinstance(value, list)
        )
        rows = payload[system]
        layers = payload[f"{system}::layers"]

    item_n = sum(int(row["rows"]) for row in rows)
    pair_n = sum(int(row["units"]) for row in rows)
    item_acc = sum(float(row["accuracy"]) * int(row["rows"]) for row in rows) / item_n
    # The official core aggregate gives every family equal weight, including
    # pair accuracy; group counts differ across generators.
    pair_acc = sum(float(row["pair_accuracy"]) for row in rows) / len(rows)
    seven_layer = sum(float(value) for value in layers.values()) / len(layers)

    families = {
        row["task"]: {
            "layer": row["layer"],
            "items": int(row["rows"]),
            "groups": int(row["units"]),
            "coverage": float(row["coverage"]),
            "accuracy": float(row["accuracy"]),
            "pair_accuracy": float(row["pair_accuracy"]),
            "level3_accuracy": float(row["levels"]["3"]["accuracy"]),
            "level3_pair_accuracy": float(row["levels"]["3"]["pair_accuracy"]),
            "auto_at_5": float(row["auto_at_5"]),
            "ece": float(row["ece"]),
        }
        for row in rows
    }

    summary = {
        "system": system,
        "items": item_n,
        "groups": pair_n,
        "accuracy": item_acc,
        "pair_accuracy": pair_acc,
        "seven_layer_score": seven_layer,
        "layers": layers,
        "families": families,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
