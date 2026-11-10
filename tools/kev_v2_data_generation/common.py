#!/usr/bin/env python3
"""Shared schema, hashing, and validation helpers for Kev-style JSONL records."""

from __future__ import annotations

import hashlib
import json
import os
import random
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


JsonObject = Dict[str, Any]


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def stable_rng(seed: int, family: str, index: int, attempt: int = 0) -> random.Random:
    material = f"kev-public-reconstruction:{seed}:{family}:{index}:{attempt}".encode("utf-8")
    digest = hashlib.sha256(material).digest()
    return random.Random(int.from_bytes(digest[:16], "big"))


def choice_question(instructions: str, options: Mapping[str, str], label: str) -> JsonObject:
    return {
        "type": "choice",
        "instructions": instructions,
        "criteria": dict(options),
        "label": label,
    }


def build_record(
    family: str,
    index: int,
    state: Any,
    instructions: str,
    options: Mapping[str, str],
    label: str,
    *,
    question_id: str = "decision",
    seed: int = 20261104,
    generator: str,
    dataset: str = "synthetic-v1",
    extra_meta: Optional[Mapping[str, Any]] = None,
) -> JsonObject:
    record_id = f"kev-public-reconstruction/{dataset}/{family}/{index:06d}"
    meta: JsonObject = {
        "id": record_id,
        "group_id": record_id,
        "source": f"kev-public-reconstruction/{family}",
        "dataset": dataset,
        "family": family,
        "split": "train",
        "variant": "clean",
        "generator": generator,
        "seed": seed,
        "state_sha256": sha256_json(state),
        "provenance": "independent_public_reconstruction_not_official_kev_data",
    }
    if extra_meta:
        meta.update(dict(extra_meta))
    record = {
        "state": state,
        "questions": {question_id: choice_question(instructions, options, label)},
        "_meta": meta,
    }
    problems = validate_record(record)
    if problems:
        raise ValueError(f"invalid generated record {record_id}: {'; '.join(problems)}")
    return record


def validate_record(record: Any) -> List[str]:
    problems: List[str] = []
    if not isinstance(record, dict):
        return ["record is not an object"]
    if record.get("state") in (None, "", {}, []):
        problems.append("state is empty")
    questions = record.get("questions")
    if not isinstance(questions, dict) or not questions:
        problems.append("questions is empty or not an object")
    else:
        for qid, question in questions.items():
            if not isinstance(question, dict):
                problems.append(f"question {qid} is not an object")
                continue
            if question.get("type") != "choice":
                problems.append(f"question {qid} must be type=choice")
            if not isinstance(question.get("instructions"), str) or not question["instructions"].strip():
                problems.append(f"question {qid} has no instructions")
            options = question.get("criteria")
            if not isinstance(options, dict) or len(options) < 2:
                problems.append(f"question {qid} needs at least two options")
            elif question.get("label") not in options:
                problems.append(f"question {qid} label is not an option key")
    meta = record.get("_meta")
    if not isinstance(meta, dict):
        problems.append("_meta is missing")
    else:
        for key in ("id", "family", "source", "provenance", "state_sha256"):
            if not meta.get(key):
                problems.append(f"_meta.{key} is missing")
        if record.get("state") not in (None, "", {}, []) and meta.get("state_sha256") != sha256_json(record["state"]):
            problems.append("_meta.state_sha256 does not match state")
    return problems


def read_jsonl(path: Path) -> List[JsonObject]:
    if not path.exists():
        return []
    rows: List[JsonObject] = []
    with path.open("r", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
    return rows


def atomic_write_jsonl(path: Path, records: Iterable[JsonObject]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def option_map(keys: Sequence[str], texts: Sequence[str]) -> Dict[str, str]:
    if len(keys) != len(texts):
        raise ValueError("option key and text counts differ")
    return dict(zip(keys, texts))


def shuffled_options(rng: random.Random, values: Sequence[Tuple[str, str]]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Return option-key -> text and semantic-value -> option-key maps."""
    items = list(values)
    rng.shuffle(items)
    keys = [chr(ord("a") + i) for i in range(len(items))]
    options = {key: text for key, (_, text) in zip(keys, items)}
    value_to_key = {value: key for key, (value, _) in zip(keys, items)}
    return options, value_to_key

