#!/usr/bin/env python3
"""Build the reviewed public GitHub archive manifest for the Kev experiments."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
KEV_ROOT = REPO / "artifacts/kev_training_eval_20261026"
OUTPUTS_ROOT = REPO / "outputs"
MANIFEST_TSV = KEV_ROOT / "PUBLIC_ARCHIVE_MANIFEST_20261110.tsv"
SUMMARY_JSON = KEV_ROOT / "PUBLIC_ARCHIVE_SUMMARY_20261110.json"
EXTRA_FILES = [
    REPO / "artifacts/jev_post_20261020_landscape_20261109.md",
    REPO / "artifacts/StartLux_AutoThink_思维链示例_20261104.md",
]

WEIGHT_SUFFIXES = {".safetensors", ".pt", ".bin", ".ckpt", ".pth"}
TOKENIZER_FILES = {
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.json",
    "merges.txt",
    "special_tokens_map.json",
    "generation_config.json",
}


def git_tracked() -> set[Path]:
    output = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", "-z", "HEAD"], cwd=REPO
    )
    return {REPO / item.decode() for item in output.split(b"\0") if item}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verified_roots() -> set[Path]:
    return {path.parent for path in KEV_ROOT.rglob("*-verified-evidence.tar.gz")}


def exclusion_reason(path: Path, verified: set[Path]) -> str | None:
    if path.name == ".env" or path.name.startswith(".env."):
        return "environment_file"
    if path.suffix.lower() in WEIGHT_SUFFIXES:
        return "model_weight"
    if path.suffix.lower() == ".pyc" or path.name == ".DS_Store" or path.name.startswith("._") or "__pycache__" in path.parts:
        return "cache"
    if path.name == "all_pairwise_question_gaps.csv":
        return "github_100mb_limit_redundant_derivative"
    if path.name in TOKENIZER_FILES or "qwen38_tokenizer" in path.parts:
        return "reproducible_tokenizer_copy"
    if "report_app" in path.parts or "decisionpivot_probability_error_report_app_20261110" in path.parts:
        if "dist" in path.parts or "content" in path.parts or path.name in {"data.json", "theme.css"}:
            return None
        return "copied_report_runtime"
    for root in verified:
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if relative.parts and relative.parts[0] in {"evidence", "baseline_evidence"}:
            return "duplicate_extracted_evidence"
    return None


def iter_files(root: Path):
    if root.is_file():
        yield root
        return
    if not root.exists():
        return
    for path in root.rglob("*"):
        if path.is_file():
            yield path


tracked = git_tracked()
verified = verified_roots()
selected: dict[Path, str] = {}
excluded: list[tuple[Path, str]] = []

for path in iter_files(KEV_ROOT):
    if path in {MANIFEST_TSV, SUMMARY_JSON}:
        continue
    if path in tracked:
        selected[path] = "already_tracked"
        continue
    reason = exclusion_reason(path, verified)
    if reason:
        excluded.append((path, reason))
    else:
        selected[path] = "new"

for root in [OUTPUTS_ROOT, REPO / "tools", REPO / "scripts"]:
    for path in iter_files(root):
        if path.name == ".env" or path.name.startswith(".env."):
            excluded.append((path, "environment_file"))
        elif path.name == ".DS_Store" or path.name.startswith("._") or path.suffix.lower() == ".pyc" or "__pycache__" in path.parts:
            excluded.append((path, "cache"))
        elif path in tracked:
            selected[path] = "already_tracked"
        else:
            selected[path] = "new"

for path in EXTRA_FILES:
    if path.exists():
        selected[path] = "already_tracked" if path in tracked else "new"

rows = []
directory_summary: dict[str, list[int]] = defaultdict(lambda: [0, 0])
for path, status in sorted(selected.items(), key=lambda item: str(item[0])):
    relative = path.relative_to(REPO)
    size = path.stat().st_size
    rows.append(
        {
            "path": str(relative),
            "bytes": size,
            "sha256": sha256(path),
            "archive_status": status,
        }
    )
    top = relative.parts[0] if relative.parts else "."
    directory_summary[top][0] += 1
    directory_summary[top][1] += size

with MANIFEST_TSV.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=["path", "bytes", "sha256", "archive_status"],
        delimiter="\t",
    )
    writer.writeheader()
    writer.writerows(rows)

excluded_counts = Counter(reason for _, reason in excluded)
excluded_bytes = Counter()
for path, reason in excluded:
    excluded_bytes[reason] += path.stat().st_size

summary = {
    "created_at": "2026-11-10",
    "repository": "wxie9/dummy-test-001",
    "branch": "codex/kev-training-logs",
    "selected_file_count_before_manifest": len(rows),
    "selected_bytes_before_manifest": sum(row["bytes"] for row in rows),
    "new_file_count_before_manifest": sum(row["archive_status"] == "new" for row in rows),
    "already_tracked_file_count": sum(row["archive_status"] == "already_tracked" for row in rows),
    "directory_summary": {
        key: {"files": value[0], "bytes": value[1]}
        for key, value in sorted(directory_summary.items())
    },
    "excluded": {
        reason: {"files": excluded_counts[reason], "bytes": excluded_bytes[reason]}
        for reason in sorted(excluded_counts)
    },
    "publication_rules": [
        "No model weights, private keys, API keys, AccessKeys, SSH passwords, or caches.",
        "Verified evidence tarballs replace their duplicate extracted evidence trees.",
        "Reproducible tokenizer copies and copied report runtimes are omitted.",
        "The >100 MB all-pairwise derivative CSV is omitted; compact analyses and portable bundles remain.",
    ],
}
SUMMARY_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(MANIFEST_TSV)
print(SUMMARY_JSON)
print(json.dumps(summary, ensure_ascii=False))
