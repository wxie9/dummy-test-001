#!/usr/bin/env python3
"""Paired before/after analysis for H20 Kev-4B and Kev-9B weak-seven runs."""

import collections
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
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
    "targeted_v2_all7_temporal": "时间与数值",
    "targeted_v2_all7_tool_routing": "工具路由",
    "targeted_v2_all7_injection": "提示注入",
    "targeted-v6-20261030/probability": "概率",
    "targeted-v6-20261030/policy": "长政策",
    "targeted-v6-20261030/multihop": "多跳推理",
}
TARGET = {
    "4b": {"时间与数值", "工具路由", "代码审查", "提示注入", "概率", "代码变更理解", "测试稳定性判断"},
    "9b": {"时间与数值", "代码审查", "工具路由", "代码变更理解", "长政策", "概率", "多跳推理"},
}


def load(path):
    return json.loads(path.read_text())


def correct(row):
    return int(row["p"].index(max(row["p"])) == row["label"])


def score(before, after):
    if len(before) != len(after):
        raise AssertionError(f"Row count mismatch: {len(before)} != {len(after)}")
    groups = collections.defaultdict(lambda: collections.Counter())
    for i, (b, a) in enumerate(zip(before, after)):
        for key in ("id", "source", "task", "type", "keys", "label", "question"):
            if b[key] != a[key]:
                raise AssertionError(f"Row {i} {key} mismatch")
        category = CATEGORY[b["source"]]
        x, y = correct(b), correct(a)
        item = groups[category]
        item["n"] += 1
        item["before"] += x
        item["after"] += y
        item["fixed"] += int(x == 0 and y == 1)
        item["broken"] += int(x == 1 and y == 0)
    return {k: dict(v) for k, v in groups.items()}


def combine(*maps):
    out = collections.defaultdict(collections.Counter)
    for mapping in maps:
        for key, counts in mapping.items():
            out[key].update(counts)
    return {key: dict(counts) for key, counts in out.items()}


def totals(mapping, selected):
    total = collections.Counter()
    for category, counts in mapping.items():
        if category in selected:
            total.update(counts)
    return dict(total)


def fmt(counts):
    n = counts["n"]
    delta = 100 * (counts["after"] - counts["before"]) / n
    return (f'{counts["before"]}/{n} ({100*counts["before"]/n:.1f}%)',
            f'{counts["after"]}/{n} ({100*counts["after"]/n:.1f}%)',
            f'{delta:+.1f} pp',
            f'{counts["fixed"]}/{counts["broken"]}')


def main():
    output = {}
    lines = [
        "# H20 Kev-4B 与 Kev-9B 定向七类续训结果", "",
        "2026-10-31。分别从 4B stage 4 和 9B stage 3 继续训练。每个模型使用 1500 条定向情境和 6000 条 decision-v7 回放，一轮、938 步；基座冻结，训练 LoRA 和已有 pointer head。准确率按子问计算；修复/新增错误由同一题前后配对统计。", "",
    ]
    for model in ("4b", "9b"):
        test = combine(*[
            score(load(ROOT / "baseline_rows" / f"kev-{model}-{slug}-rows.json"),
                  load(ROOT / "post_rows" / f"kev-{model}-{slug}-rows.json"))
            for slug in ("hard", "dev")
        ])
        dev = score(load(ROOT / "development_rows" / f"kev-{model}-before-rows.json"),
                    load(ROOT / "development_rows" / f"kev-{model}-after-rows.json"))
        output[model] = {"test": test, "development": dev,
                         "target_test": totals(test, TARGET[model]),
                         "other_test": totals(test, set(test) - TARGET[model]),
                         "all_test": totals(test, set(test)),
                         "target_development": totals(dev, TARGET[model])}
        lines += [f"## {model.upper()}", "", "### 冻结 hard-v1 与 devtools-v1", "",
                  "| 类别 | 续训前 | 续训后 | 变化 | 修复/新增错误 |", "|---|---:|---:|---:|---:|"]
        for category, counts in sorted(test.items(), key=lambda item: item[1]["before"] / item[1]["n"]):
            label = f"{category}（目标）" if category in TARGET[model] else category
            lines.append("| " + label + " | " + " | ".join(fmt(counts)) + " |")
        for key, label in [("target_test", "目标七类"), ("other_test", "其他六类"), ("all_test", "两套测试合计")]:
            lines.append("| **" + label + "** | " + " | ".join(fmt(output[model][key])) + " |")
        lines += ["", "### 未参与训练的开发题", "",
                  "| 类别 | 续训前 | 续训后 | 变化 | 修复/新增错误 |", "|---|---:|---:|---:|---:|"]
        for category, counts in sorted(dev.items(), key=lambda item: item[1]["before"] / item[1]["n"]):
            lines.append("| " + category + " | " + " | ".join(fmt(counts)) + " |")
        lines.append("| **开发题合计** | " + " | ".join(fmt(output[model]["target_development"])) + " |")
        lines.append("")
        lines += ["### 六套冻结测试", "", "| 测试集 | 题数 | 续训前 | 续训后 | 变化 |", "|---|---:|---:|---:|---:|"]
        output[model]["six_suites"] = {}
        for suite in ("decision-v7", "transfer-v4", "transfer-v9", "hard-v1", "devtools-v1", "documents-v1"):
            before_report = load(ROOT / "baseline_six_reports" / model / suite / "report.json")
            after_report = load(ROOT / "post_six_reports" / model / suite / "report.json")
            before_n = before_report["clean"]["n"]
            after_n = after_report["clean"]["n"]
            if before_n != after_n or before_report["suite_sha256"] != after_report["suite_sha256"]:
                raise AssertionError(f"Suite mismatch: {model} {suite}")
            if after_report["coverage"]["rejected_records"] or after_report["coverage"]["truncated_records"]:
                raise AssertionError(f"Incomplete after coverage: {model} {suite}")
            b, a = before_report["clean"]["acc"], after_report["clean"]["acc"]
            output[model]["six_suites"][suite] = {"n": before_n, "before": b, "after": a, "delta_pp": 100 * (a - b)}
            lines.append(f"| {suite} | {before_n} | {100*b:.2f}% | {100*a:.2f}% | {100*(a-b):+.2f} pp |")
        lines.append("")
    lines += [
        "## 判断与限制", "",
        "两模型的目标七类在 hard-v1 与 devtools-v1 上均有小幅净增，但其他六类均下降。4B 的提升主要来自提示注入和工具路由；9B 在长政策和工具路由上进步，代码审查、多跳推理未改善。六套测试并未一致提升，因此本次检查点保留为候选，不替换原检查点。", "",
        "七类是根据这两套测试的续训前成绩选出的，所以它们的续训后变化是诊断结果，不是新的盲测。开发题未逐题进入本次定向训练，但与训练题共享来源或模板；开发题增幅不能等同于新来源泛化。此次每个模型只跑一个随机种子，尚不能估计波动。", "",
        "逐题结果、训练配置、输入清单与 SHA256、六套测试报告均保存在本目录；模型权重保存在 H20 的 `/data/kev/runs/h20-{4b,9b}-weak7-v6-20261031/`。", "",
    ]
    (ROOT / "analysis.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    (ROOT / "results.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
