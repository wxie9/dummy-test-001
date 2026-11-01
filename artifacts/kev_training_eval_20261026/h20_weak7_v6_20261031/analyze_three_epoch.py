#!/usr/bin/env python3
"""Audit and compare original, one-epoch, and three-epoch H20 Kev runs."""

import collections
import hashlib
import json
from pathlib import Path

from analyze_results import CATEGORY, TARGET

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "three_epoch_raw" / "runs"
SUITES = ("decision-v7", "transfer-v4", "transfer-v9", "hard-v1", "devtools-v1", "documents-v1")
RUNS = {
    "4b": ("h20-4b-eval-six-20261030", "h20-4b-weak7-v6-20261031", "h20-4b-weak7-v6-3ep-20261031"),
    "9b": ("h20-9b-eval-six-raw-20261030", "h20-9b-weak7-v6-20261031", "h20-9b-weak7-v6-3ep-4gpu-20261031"),
}


def read(path):
    return json.loads(path.read_text())


def correct(row):
    return int(row["p"].index(max(row["p"])) == row["label"])


def clean_rows(rows, suite):
    return [r for r in rows if r["variant"] == "clean" and not (suite == "transfer-v9" and r["source"] == "unknowable")]


def paired(rows):
    assert len({len(x) for x in rows}) == 1
    counts = collections.Counter()
    for i, triple in enumerate(zip(*rows)):
        for key in ("id", "source", "task", "type", "variant", "keys", "label", "question"):
            assert triple[0][key] == triple[1][key] == triple[2][key], (i, key)
        a, b, c = map(correct, triple)
        counts.update(n=1, original=a, one=b, three=c,
                      fixed_03=int(a == 0 and c == 1), broken_03=int(a == 1 and c == 0),
                      fixed_13=int(b == 0 and c == 1), broken_13=int(b == 1 and c == 0))
    return dict(counts)


def grouped(rows):
    by_category = collections.defaultdict(lambda: [[], [], []])
    for triple in zip(*rows):
        cat = CATEGORY[triple[0]["source"]]
        for j, row in enumerate(triple):
            by_category[cat][j].append(row)
    return {k: paired(v) for k, v in by_category.items()}


def aggregate(groups, selected):
    out = collections.Counter()
    for key, data in groups.items():
        if key in selected:
            out.update(data)
    return dict(out)


def percent(data, key):
    return 100 * data[key] / data["n"]


def main():
    result = {"models": {}, "audit": {"suite_hashes_match": True, "denominators_match": True,
                                      "complete_coverage": True, "question_identity_match": True}}
    lines = ["# H20 Kev 4B/9B 三轮定向续训结果", "",
             "原始检查点、一轮候选、三轮候选均在相同冻结测试题上逐题配对。三轮是从原始检查点重新训练，**不是**在一轮候选上再加两轮。", ""]
    for model, (base_run, one_run, three_run) in RUNS.items():
        status = (RAW / (three_run + "-eval") / "status.log").read_text()
        assert f"ALL_DONE model={model}" in status
        assert "FAILED" not in status
        one_config = read(RAW / one_run / "training_config.json")["args"]
        three_config = read(RAW / three_run / "training_config.json")["args"]
        for key in ("base", "base_revision", "data", "replay", "seed", "lr", "lora", "max_state",
                    "p_none", "p_none_distract", "p_distract", "p_none_pair"):
            assert one_config[key] == three_config[key], (model, key)
        assert one_config["epochs"] == 1 and three_config["epochs"] == 3
        one_metrics = read(RAW / one_run / "training_metrics.json")
        three_metrics = read(RAW / three_run / "training_metrics.json")
        assert one_metrics["optimizer_steps"] == 938 and three_metrics["optimizer_steps"] == 2814
        for met in (one_metrics, three_metrics):
            assert met["rejected_records"] == met["truncated_records"] == 0
        assert one_config["batch"] * one_config["accum"] * one_metrics["world_size"] == 8
        assert three_config["batch"] * three_config["accum"] * three_metrics["world_size"] == 8
        train_file = ROOT / f"train_{model}.jsonl"
        training_sha = hashlib.sha256(train_file.read_bytes()).hexdigest()
        manifest = read(ROOT / "manifest.json")
        assert training_sha == manifest["models"][model]["sha256"]

        model_data = {"training": {"one": one_metrics, "three": three_metrics,
                                   "input_sha256": training_sha}, "suites": {}, "categories": {}}
        lines += [f"## {model.upper()}", "", "| 六套测试集 | 原始 | 一轮 | 三轮 | 三轮−原始 | 三轮−一轮 |", "|---|---:|---:|---:|---:|---:|"]
        suite_totals = collections.Counter()
        category_rows = [[], [], []]
        for suite in SUITES:
            dirs = (RAW / base_run / suite, RAW / (one_run + "-eval") / suite,
                    RAW / (three_run + "-eval") / suite)
            reports = [read(d / "report.json") for d in dirs]
            assert len({r["suite_sha256"] for r in reports}) == 1, (model, suite, "hash")
            assert len({r["clean"]["n"] for r in reports}) == 1, (model, suite, "n")
            for report in reports:
                coverage = report["coverage"]
                assert coverage["requested_records"] == coverage["evaluated_records"]
                assert coverage["requested_questions"] == coverage["evaluated_questions"]
                assert coverage["rejected_records"] == coverage["truncated_records"] == 0
            all_rows = [read(d / "rows.json") for d in dirs]
            rows = [clean_rows(x, suite) for x in all_rows]
            stat = paired(rows)
            assert stat["n"] == reports[0]["clean"]["n"]
            for key, report in zip(("original", "one", "three"), reports):
                assert round(report["clean"]["acc"] * stat["n"]) == stat[key], (model, suite, key)
            stat["suite_sha256"] = reports[0]["suite_sha256"]
            stat["coverage"] = reports[2]["coverage"]
            model_data["suites"][suite] = stat
            suite_totals.update({k: stat[k] for k in ("n", "original", "one", "three", "fixed_03", "broken_03", "fixed_13", "broken_13")})
            lines.append(f"| {suite} ({stat['n']}) | {percent(stat,'original'):.2f}% | {percent(stat,'one'):.2f}% | {percent(stat,'three'):.2f}% | {100*(stat['three']-stat['original'])/stat['n']:+.2f} pp | {100*(stat['three']-stat['one'])/stat['n']:+.2f} pp |")
            if suite in ("hard-v1", "devtools-v1"):
                for j in range(3):
                    category_rows[j].extend(rows[j])
        model_data["six_total"] = dict(suite_totals)
        lines.append(f"| **六套加权合计 ({suite_totals['n']})** | {percent(suite_totals,'original'):.2f}% | {percent(suite_totals,'one'):.2f}% | {percent(suite_totals,'three'):.2f}% | {100*(suite_totals['three']-suite_totals['original'])/suite_totals['n']:+.2f} pp | {100*(suite_totals['three']-suite_totals['one'])/suite_totals['n']:+.2f} pp |")
        categories = grouped(category_rows)
        model_data["categories"] = categories
        model_data["target_seven"] = aggregate(categories, TARGET[model])
        model_data["other_six"] = aggregate(categories, set(categories) - TARGET[model])
        lines += ["", "| hard+devtools 分类 | 原始 | 一轮 | 三轮 | 三轮−原始 | 三轮−一轮 |", "|---|---:|---:|---:|---:|---:|"]
        for cat, data in sorted(categories.items(), key=lambda kv: kv[1]["original"] / kv[1]["n"]):
            label = cat + ("（目标）" if cat in TARGET[model] else "")
            lines.append(f"| {label} ({data['n']}) | {percent(data,'original'):.1f}% | {percent(data,'one'):.1f}% | {percent(data,'three'):.1f}% | {100*(data['three']-data['original'])/data['n']:+.1f} pp | {100*(data['three']-data['one'])/data['n']:+.1f} pp |")
        for key, label in (("target_seven", "目标七类"), ("other_six", "其余六类")):
            data = model_data[key]
            lines.append(f"| **{label} ({data['n']})** | {percent(data,'original'):.2f}% | {percent(data,'one'):.2f}% | {percent(data,'three'):.2f}% | {100*(data['three']-data['original'])/data['n']:+.2f} pp | {100*(data['three']-data['one'])/data['n']:+.2f} pp |")
        before_dev = read(ROOT / "development_rows" / f"kev-{model}-before-rows.json")
        one_dev = read(ROOT / "development_rows" / f"kev-{model}-after-rows.json")
        three_dev = read(RAW / (three_run + "-dev-after") / "rows.json")
        dev = paired([before_dev, one_dev, three_dev])
        dev_reports = [read(ROOT / "development_rows" / f"kev-{model}-before-report.json"),
                       read(ROOT / "development_rows" / f"kev-{model}-after-report.json"),
                       read(RAW / (three_run + "-dev-after") / "report.json")]
        assert len({r["suite_sha256"] for r in dev_reports}) == 1
        assert len({r["clean"]["n"] for r in dev_reports}) == 1
        for key, report in zip(("original", "one", "three"), dev_reports):
            assert report["clean"]["n"] == dev["n"]
            assert round(report["clean"]["acc"] * dev["n"]) == dev[key]
            cov = report["coverage"]
            assert cov["requested_records"] == cov["evaluated_records"]
            assert cov["requested_questions"] == cov["evaluated_questions"]
            assert cov["rejected_records"] == cov["truncated_records"] == 0
        dev["suite_sha256"] = dev_reports[0]["suite_sha256"]
        model_data["development"] = dev
        lines += ["", f"开发题：{dev['original']}/{dev['n']} → {dev['one']}/{dev['n']} → {dev['three']}/{dev['n']}；三轮相对原始 {100*(dev['three']-dev['original'])/dev['n']:+.2f} pp，相对一轮 {100*(dev['three']-dev['one'])/dev['n']:+.2f} pp。", ""]
        result["models"][model] = model_data
    lines += ["## 判断", "",
              "- 4B 三轮在六套测试合计比原始少 39/5999 道正确题，比一轮少 41 道；目标七类 837→853→836/1173，三轮收益已消失。",
              "- 9B 三轮在六套测试合计比原始少 46/5999 道正确题，比一轮少 41 道；目标七类 910→919→913/1198，仍比原始多 3 道，但其余类别与其他测试集下降。",
              "- 开发题继续上升（4B 568→579→582/813；9B 585→640→651/839），冻结测试却回落。这与训练来源附近的拟合增强、跨测试来源迁移不足相符；单次实验不能确定唯一原因。",
              "- 因为六套总分和多个测试集下降，三轮检查点不替换原始检查点，也不优于一轮候选。", "",
              "## 核对与限制", "", "六套测试和开发题在三个检查点间的 suite SHA256、clean 分母一致；逐题身份完全匹配；训练与评测均无拒绝或截断。", "",
              "七类根据原始 hard-v1/devtools-v1 成绩选出，这些结果属于已接触测试集上的诊断，不是独立盲测。每种配置一个随机种子。4B 一轮与三轮都用单卡；9B 一轮用单卡、三轮用四卡且有效 batch 相同，所以 9B 差异不能单独归因于训练轮数。", ""]
    (ROOT / "three_epoch_comparison.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (ROOT / "three_epoch_results.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
