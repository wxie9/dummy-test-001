#!/usr/bin/env python3
"""Validate and compare the expanded weak-seven H20 runs.

The comparison is paired at the scored-question level across the original
checkpoint, the previous one-round weak7 checkpoint, and this expanded-data
checkpoint.  Reports and rows come from the same six frozen suites.
"""

from __future__ import annotations

import collections
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREV = ROOT.parent / "h20_weak7_v6_20261031"
SUITES = ("decision-v7", "transfer-v4", "transfer-v9", "hard-v1", "devtools-v1", "documents-v1")
CATEGORY = {
    "hard_temporal_numeric": "时间与数值",
    "when2call": "工具路由",
    "codereviewer": "代码审查",
    "prompt_injection": "提示注入",
    "hard_probability": "概率",
    "commitpackft": "代码变更理解",
    "flakeflagger": "测试稳定性判断",
    "hard_judge": "计算结果核验",
    "hard_long_policy": "长政策",
    "hard_multi_hop": "多跳推理",
    "hard_ambiguous": "信息不足",
    "aegis": "安全风险判断",
    "hard_tradeoff": "多约束权衡决策",
}
TARGET = {
    "4b": {"时间与数值", "工具路由", "代码审查", "提示注入", "概率", "代码变更理解", "测试稳定性判断"},
    "9b": {"时间与数值", "代码审查", "工具路由", "代码变更理解", "长政策", "概率", "多跳推理"},
}


def load(path: Path):
    return json.loads(path.read_text())


def current_base(model: str) -> Path:
    name = (
        f"h20-{model}-weak7-neighborhood-expansion-e1-"
        f"{'2gpu' if model == '4b' else '4gpu'}-20261101"
    )
    return ROOT / "archive" / model / name


def original_base(model: str) -> Path:
    name = f"h20-{model}-eval-six{'-raw' if model == '9b' else ''}-20261030"
    return PREV / "three_epoch_raw" / "runs" / name


def previous_base(model: str) -> Path:
    return PREV / "three_epoch_raw" / "runs" / f"h20-{model}-weak7-v6-20261031-eval"


def scored(rows):
    return [r for r in rows if r["variant"] == "clean" and r["source"] != "unknowable"]


def key(row):
    return (row["id"], row["question"])


def indexed(rows):
    """Map rows without dropping duplicate questions shared by two suites."""
    seen = collections.Counter()
    out = {}
    for row in scored(rows):
        base = key(row)
        occurrence = seen[base]
        seen[base] += 1
        out[(*base, occurrence)] = row
    return out


def correct(row):
    return int(max(range(len(row["p"])), key=row["p"].__getitem__) == row["label"])


def paired(left_rows, right_rows):
    left = indexed(left_rows)
    right = indexed(right_rows)
    if left.keys() != right.keys():
        raise AssertionError(f"paired key mismatch: left-only={len(left.keys()-right.keys())}, right-only={len(right.keys()-left.keys())}")
    counts = collections.Counter(n=len(left))
    for k, a in left.items():
        b = right[k]
        for field in ("source", "task", "type", "keys", "label", "question"):
            if a[field] != b[field]:
                raise AssertionError(f"paired field mismatch for {k}: {field}")
        x, y = correct(a), correct(b)
        counts["left"] += x
        counts["right"] += y
        counts["fixed"] += int(x == 0 and y == 1)
        counts["broken"] += int(x == 1 and y == 0)
    return dict(counts)


def triple_by_category(original_rows, previous_rows, current_rows):
    maps = [indexed(rows) for rows in (original_rows, previous_rows, current_rows)]
    if not (maps[0].keys() == maps[1].keys() == maps[2].keys()):
        raise AssertionError("category comparison requires identical rows")
    out = collections.defaultdict(collections.Counter)
    for k, row in maps[0].items():
        category = CATEGORY[row["source"]]
        item = out[category]
        item["n"] += 1
        item["original"] += correct(row)
        item["previous"] += correct(maps[1][k])
        item["expanded"] += correct(maps[2][k])
    return {name: dict(values) for name, values in out.items()}


def aggregate_categories(categories, selected):
    total = collections.Counter()
    for category, values in categories.items():
        if category in selected:
            total.update(values)
    return dict(total)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fmt_acc(value):
    return f"{100 * value:.2f}%"


def mcnemar_exact(fixed: int, broken: int) -> float:
    """Two-sided exact binomial test for paired discordant outcomes."""
    n = fixed + broken
    if not n:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(fixed, broken) + 1)) / (2**n)
    return min(1.0, 2 * tail)


def main():
    result = {"models": {}, "validation": {"all_checks_passed": True}}
    lines = [
        "# Kev 4B/9B 扩充 weak7 数据续训结果",
        "",
        "2026-11-01。两模型都从原始 stage checkpoint 重新训练一轮，而不是从上一轮 weak7 checkpoint 接着训练。4B 使用两卡，9B 使用四卡；均混入 6,000 条 decision-v7 replay。比较对象为原始 checkpoint、上一轮 1,500 条 weak7 候选，以及本轮合并错题邻域与独立扩充数据的候选。",
        "",
    ]
    for model in ("4b", "9b"):
        model_out = {"suites": {}, "categories": {}}
        result["models"][model] = model_out
        run = current_base(model)
        eval_root = Path(str(run) + "-eval")
        dev_root = Path(str(run) + "-development-fixed")
        metrics = load(ROOT / "archive" / model / "training_metrics.json")
        model_out["training"] = {
            k: metrics[k]
            for k in ("wall_seconds", "requested_records", "records_seen", "optimizer_steps", "forward_tokens", "world_size", "truncated_records", "rejected_records")
        }
        pooled = collections.Counter()
        hard_rows = {"original": [], "previous": [], "expanded": []}
        lines += [f"## {model.upper()}", "", "### 训练", ""]
        lines.append(
            f"- wall time {metrics['wall_seconds']/60:.1f} 分钟，world size {metrics['world_size']}，optimizer steps {metrics['optimizer_steps']}，训练 rejected/truncated 均为 {metrics['rejected_records']}/{metrics['truncated_records']}。"
        )
        lines += ["", "### 六套冻结测试", "", "| 测试集 | n | 原始 | 上一轮 weak7 | 本轮扩充 | 本轮−原始 | 本轮−上一轮 | 修复/破坏（对原始） |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for suite in SUITES:
            dirs = {
                "original": original_base(model) / suite,
                "previous": previous_base(model) / suite,
                "expanded": eval_root / suite,
            }
            reports = {name: load(path / "report.json") for name, path in dirs.items()}
            rows = {name: load(path / "rows.json") for name, path in dirs.items()}
            suite_hashes = {report["suite_sha256"] for report in reports.values()}
            ns = {report["clean"]["n"] for report in reports.values()}
            if len(suite_hashes) != 1 or len(ns) != 1:
                raise AssertionError(f"suite mismatch: {model} {suite}")
            coverage = reports["expanded"]["coverage"]
            if coverage["rejected_records"] or coverage["truncated_records"] or coverage["requested_records"] != coverage["evaluated_records"]:
                raise AssertionError(f"incomplete coverage: {model} {suite}: {coverage}")
            for name in dirs:
                calculated = sum(correct(r) for r in scored(rows[name])) / len(scored(rows[name]))
                if abs(calculated - reports[name]["clean"]["acc"]) > 1e-12:
                    raise AssertionError(f"row/report accuracy mismatch: {model} {suite} {name}")
            orig_pair = paired(rows["original"], rows["expanded"])
            prev_pair = paired(rows["previous"], rows["expanded"])
            acc = {name: reports[name]["clean"]["acc"] for name in reports}
            n = next(iter(ns))
            entry = {
                "n": n,
                "suite_sha256": next(iter(suite_hashes)),
                "coverage": coverage,
                "accuracy": acc,
                "expanded_minus_original_pp": 100 * (acc["expanded"] - acc["original"]),
                "expanded_minus_previous_pp": 100 * (acc["expanded"] - acc["previous"]),
                "paired_vs_original": orig_pair,
                "paired_vs_previous": prev_pair,
            }
            model_out["suites"][suite] = entry
            for name in ("original", "previous", "expanded"):
                pooled[name] += round(acc[name] * n)
            pooled["n"] += n
            pooled["fixed_original"] += orig_pair["fixed"]
            pooled["broken_original"] += orig_pair["broken"]
            pooled["fixed_previous"] += prev_pair["fixed"]
            pooled["broken_previous"] += prev_pair["broken"]
            lines.append(
                f"| {suite} | {n} | {fmt_acc(acc['original'])} | {fmt_acc(acc['previous'])} | {fmt_acc(acc['expanded'])} | {entry['expanded_minus_original_pp']:+.2f} pp | {entry['expanded_minus_previous_pp']:+.2f} pp | {orig_pair['fixed']}/{orig_pair['broken']} |"
            )
            if suite in ("hard-v1", "devtools-v1"):
                for name in hard_rows:
                    hard_rows[name].extend(rows[name])
        model_out["pooled_six"] = dict(pooled)
        model_out["pooled_six"]["mcnemar_exact_vs_original"] = mcnemar_exact(pooled["fixed_original"], pooled["broken_original"])
        model_out["pooled_six"]["mcnemar_exact_vs_previous"] = mcnemar_exact(pooled["fixed_previous"], pooled["broken_previous"])
        lines.append(
            f"| **六套加权合计** | **{pooled['n']}** | **{100*pooled['original']/pooled['n']:.2f}%** | **{100*pooled['previous']/pooled['n']:.2f}%** | **{100*pooled['expanded']/pooled['n']:.2f}%** | **{100*(pooled['expanded']-pooled['original'])/pooled['n']:+.2f} pp** | **{100*(pooled['expanded']-pooled['previous'])/pooled['n']:+.2f} pp** | **{pooled['fixed_original']}/{pooled['broken_original']}** |"
        )
        lines.append("")
        lines.append(
            f"六套逐题配对 McNemar exact：本轮 vs 原始 `p={model_out['pooled_six']['mcnemar_exact_vs_original']:.4g}`；本轮 vs 上一轮 `p={model_out['pooled_six']['mcnemar_exact_vs_previous']:.4g}`。"
        )

        categories = triple_by_category(hard_rows["original"], hard_rows["previous"], hard_rows["expanded"])
        model_out["categories"] = categories
        target_total = aggregate_categories(categories, TARGET[model])
        other_total = aggregate_categories(categories, set(categories) - TARGET[model])
        model_out["category_aggregates"] = {"target_seven": target_total, "other": other_total}
        lines += ["", "### hard-v1 + devtools-v1 分类", "", "| 类别 | n | 原始 | 上一轮 | 本轮扩充 | 本轮−原始 | 本轮−上一轮 |", "|---|---:|---:|---:|---:|---:|---:|"]
        for category, values in sorted(categories.items(), key=lambda item: item[1]["original"] / item[1]["n"]):
            n = values["n"]
            mark = "（目标）" if category in TARGET[model] else ""
            lines.append(
                f"| {category}{mark} | {n} | {100*values['original']/n:.1f}% | {100*values['previous']/n:.1f}% | {100*values['expanded']/n:.1f}% | {100*(values['expanded']-values['original'])/n:+.1f} pp | {100*(values['expanded']-values['previous'])/n:+.1f} pp |"
            )
        for label, values in (("目标七类合计", target_total), ("其他类别合计", other_total)):
            n = values["n"]
            lines.append(
                f"| **{label}** | **{n}** | **{100*values['original']/n:.1f}%** | **{100*values['previous']/n:.1f}%** | **{100*values['expanded']/n:.1f}%** | **{100*(values['expanded']-values['original'])/n:+.1f} pp** | **{100*(values['expanded']-values['previous'])/n:+.1f} pp** |"
            )

        dev_report = load(dev_root / "report.json")
        dev_rows = load(dev_root / "rows.json")
        if dev_report["coverage"]["rejected_records"] or dev_report["coverage"]["truncated_records"]:
            raise AssertionError(f"development incomplete: {model}")
        model_out["development"] = {
            "clean": dev_report["clean"],
            "coverage": dev_report["coverage"],
            "rows": len(dev_rows),
            "suite_sha256": dev_report["suite_sha256"],
        }
        dev_parts = {}
        for name, predicate in {
            "error_neighborhood": lambda source: "error-neighborhood" in source,
            "independent_development": lambda source: "independent-expansion" in source,
        }.items():
            subset = [r for r in scored(dev_rows) if predicate(r["source"])]
            dev_parts[name] = {"n": len(subset), "correct": sum(correct(r) for r in subset)}
        model_out["development"]["partitions"] = dev_parts
        lines += ["", "### 合并 development（本轮 checkpoint）", ""]
        lines.append(
            f"- {dev_report['clean']['n']} 个计分子问，准确率 {fmt_acc(dev_report['clean']['acc'])}；evaluated questions {dev_report['coverage']['evaluated_questions']}，rejected/truncated = {dev_report['coverage']['rejected_records']}/{dev_report['coverage']['truncated_records']}。"
        )
        lines.append(
            f"- 其中错题邻域部分 {dev_parts['error_neighborhood']['correct']}/{dev_parts['error_neighborhood']['n']}（{100*dev_parts['error_neighborhood']['correct']/dev_parts['error_neighborhood']['n']:.2f}%），独立新增 development {dev_parts['independent_development']['correct']}/{dev_parts['independent_development']['n']}（{100*dev_parts['independent_development']['correct']/dev_parts['independent_development']['n']:.2f}%）。"
        )
        lines.append("- 原始与上一轮 checkpoint 没有在新增的独立 development 上跑过，因此这里不伪造前后差值；主比较使用六套完全相同的冻结测试逐题配对。")
        lines.append("")

    lines += [
        "## 结论",
        "",
        "- **4B 的扩充数据训练有效，但增益高度集中。** 六套冻结测试加权准确率从 82.00% 提到 83.41%（+1.42 pp；逐题配对 p=2.81e-05），也比上一轮 82.03% 高 1.38 pp。目标七类在 hard-v1 + devtools-v1 上合计 +7.4 pp，但其他类别合计 -1.2 pp；最大增益来自提示注入、测试稳定性判断和代码类，工具路由反而低于原始 0.7 pp。4B 可保留为强候选，但不应只凭总分直接覆盖原始 checkpoint。",
        "- **9B 有方向性增益，但整体证据还不够强。** 六套加权从 84.65% 到 85.08%（+0.43 pp；p=0.1336），相对上一轮 +0.52 pp（p=0.0611）。hard-v1 大涨 3.86 pp，长政策、时间数值、概率和多跳改善，但工具路由下降 6.0 pp，transfer-v4/v9 与 documents 也小幅回落。当前更适合作为针对性候选，不建议替换默认 9B。",
        "- **development 结果只能作为候选内诊断。** 新增独立 development 的当前准确率较高（4B 82.08%，9B 81.65%），但原始和上一轮没有在这批新题上评测，不能写成提升幅度。",
        "- hard-v1/devtools-v1 的弱类用于选题和定向训练，因此分类增益不是完全盲测；六套冻结测试的逐题配对是本报告的主证据。当前仍只有一个训练 seed。",
        "",
    ]

    archive_files = sorted(p for p in (ROOT / "archive").rglob("*") if p.is_file())
    hashes = [f"{sha256(path)}  {path.relative_to(ROOT)}" for path in archive_files]
    (ROOT / "archive_sha256.txt").write_text("\n".join(hashes) + "\n")
    result["archive"] = {"files": len(archive_files), "sha256_manifest": "archive_sha256.txt"}
    (ROOT / "expanded_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (ROOT / "expanded_results.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
