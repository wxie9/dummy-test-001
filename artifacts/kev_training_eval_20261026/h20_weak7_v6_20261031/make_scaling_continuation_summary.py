#!/usr/bin/env python3
"""Build the user-facing scaling and continuation summary from audited results."""

import json
from pathlib import Path

from analyze_results import TARGET

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
SIX = ("decision-v7", "transfer-v4", "transfer-v9", "hard-v1", "devtools-v1", "documents-v1")


def load(path):
    return json.loads(path.read_text())


def pct(count, n):
    return f"{100 * count / n:.2f}%"


def entry(stat, key):
    return f"{stat[key]}/{stat['n']} ({pct(stat[key], stat['n'])})"


def delta(stat, key):
    return f"{100 * (stat[key] - stat['original']) / stat['n']:+.2f} pp"


def delta_three_one(stat):
    return f"{100 * (stat['three'] - stat['one']) / stat['n']:+.2f} pp"


def main():
    audit = load(HERE / "three_epoch_comparison.json")
    assert all(audit["audit"].values())
    models = audit["models"]
    original_08 = {}
    for suite in SIX:
        report = load(EXPERIMENT / "runs" / "replica-20261026" / "benchmarks" / (suite + "-test") / "report.json")
        n = report["clean"]["n"]
        correct = round(report["clean"]["acc"] * n)
        for model in ("4b", "9b"):
            stat = models[model]["suites"][suite]
            assert stat["n"] == n and stat["suite_sha256"] == report["suite_sha256"]
        original_08[suite] = (correct, n)

    lines = [
        "# Kev 0.8B / 4B / 9B 规模对比与 4B / 9B 七类续训",
        "",
        "2026-10-31。口径：同一六套冻结测试集的 clean accuracy，分母按子问计；百分比变化使用百分点（pp）。所有比较的 suite SHA256 与 clean 分母一致。",
        "",
        "## 1. 原始检查点的规模对比",
        "",
        "| 测试集 | 子问数 | 0.8B（stage 3） | 4B（stage 4） | 9B（stage 3） |",
        "|---|---:|---:|---:|---:|",
    ]
    totals = {"0.8b": [0, 0], "4b": [0, 0], "9b": [0, 0]}
    for suite in SIX:
        c08, n = original_08[suite]
        b4 = models["4b"]["suites"][suite]["original"]
        b9 = models["9b"]["suites"][suite]["original"]
        lines.append(f"| {suite} | {n} | {pct(c08,n)} | {pct(b4,n)} | {pct(b9,n)} |")
        for label, c in (("0.8b", c08), ("4b", b4), ("9b", b9)):
            totals[label][0] += c
            totals[label][1] += n
    assert {k: v[1] for k, v in totals.items()} == {"0.8b": 5999, "4b": 5999, "9b": 5999}
    lines += [
        f"| **六套按子问加权** | **5999** | **{pct(*totals['0.8b'])}** | **{pct(*totals['4b'])}** | **{pct(*totals['9b'])}** |",
        "",
        "这三个模型均以 Qwen3.5 Base 为基座，但模型大小、训练阶段及训练数据不完全相同。表中是检查点之间的观察差异，不能当作只改变参数规模的受控实验。9B 在六套中的五套高于 4B；decision-v7 低 0.25 pp。devtools-v1 沿用原始测试文件的 1073 子问口径（其中两条复用同一 ID），与此前本地比较一致。",
        "",
        "## 2. 七类定向续训的设置与总体结果",
        "",
        "4B 从原 stage 4、9B 从原 stage 3 分别重启。各自挑选原始 hard-v1 与 devtools-v1 最弱的七类；每个模型使用 1500 条定向记录与 6000 条 decision-v7 回放，LoRA rank 16、有效 batch 8、seed 101、LR 1e-5。一轮为 938 步，三轮为 2814 步。4B 两次均用单卡；9B 一轮单卡、三轮四卡。三轮是从原始检查点重训，不是接在一轮检查点后面。",
        "",
        "| 模型与口径 | 原始 | 一轮 | 三轮 | 一轮−原始 | 三轮−原始 | 三轮−一轮 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for model in ("4b", "9b"):
        m = models[model]
        for label, stat in (("目标七类（hard+devtools）", m["target_seven"]),
                            ("其余六类（hard+devtools）", m["other_six"]),
                            ("六套加权合计", m["six_total"]),
                            ("开发题", m["development"])):
            lines.append(f"| {model.upper()} · {label} | {entry(stat,'original')} | {entry(stat,'one')} | {entry(stat,'three')} | {delta(stat,'one')} | {delta(stat,'three')} | {delta_three_one(stat)} |")

    lines += ["", "## 3. 实际训练的七类题：准确率如何变", "",
              "以下类别按各模型原始正确率从低到高排序。数值是 hard-v1 与 devtools-v1 冻结测试中对应类别的子问，不是训练集准确率；两模型目标七类名单不同。", ""]
    for model in ("4b", "9b"):
        categories = models[model]["categories"]
        lines += [f"### {model.upper()} 的七类", "",
                  "| 类别 | 子问数 | 原始 | 一轮 | 三轮 | 一轮−原始 | 三轮−原始 | 三轮−一轮 |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for name in sorted(TARGET[model], key=lambda x: categories[x]["original"] / categories[x]["n"]):
            stat = categories[name]
            lines.append(f"| {name} | {stat['n']} | {entry(stat,'original')} | {entry(stat,'one')} | {entry(stat,'three')} | {delta(stat,'one')} | {delta(stat,'three')} | {delta_three_one(stat)} |")
        stat = models[model]["target_seven"]
        lines.append(f"| **目标七类合计** | **{stat['n']}** | **{entry(stat,'original')}** | **{entry(stat,'one')}** | **{entry(stat,'three')}** | **{delta(stat,'one')}** | **{delta(stat,'three')}** | **{delta_three_one(stat)}** |")
        lines.append("")

    lines += ["## 4. 六套测试在续训后的变化", "",
              "| 模型 | 测试集 | 原始 | 一轮 | 三轮 | 三轮−原始 |",
              "|---|---|---:|---:|---:|---:|"]
    for model in ("4b", "9b"):
        for suite in SIX:
            stat = models[model]["suites"][suite]
            lines.append(f"| {model.upper()} | {suite} | {pct(stat['original'],stat['n'])} | {pct(stat['one'],stat['n'])} | {pct(stat['three'],stat['n'])} | {delta(stat,'three')} |")
    lines += ["", "## 5. 目前能下的结论", "",
              "- 原始检查点的六套加权准确率为 0.8B 71.38%、4B 82.00%、9B 84.65%；这些差异同时含训练阶段与数据差异。",
              "- 一轮续训在目标七类带来小幅提升（4B +1.36 pp，9B +0.75 pp），其余六类均下降；六套合计 4B 基本持平（+0.03 pp），9B 略降（−0.08 pp）。",
              "- 三轮续训的开发题继续提升，但六套合计 4B 比原始低 0.65 pp、9B 低 0.77 pp；4B 目标七类的增益消失，9B 目标七类仅比原始多 3/1198 道。故三轮权重不替换原始检查点。",
              "- 七类是依据这些测试题的原始成绩选择的；上述类别变化是诊断，不是新盲测。每个配置只有一个 seed。9B 一轮与三轮还改变了 GPU 数，不能把差异全部归因于轮数。",
              "",
              "## 原始证据", "",
              "- 0.8B 原始六套报告：`../runs/replica-20261026/benchmarks/`；4B/9B 原始、一轮、三轮逐题及报告：`three_epoch_raw/`。",
              "- 逐题核对与机器可读计数：`three_epoch_comparison.json`；详细三轮报告：`three_epoch_results.md`；一轮报告：`results.md`。",
              "- 0.8B 与 4B/9B 的套件哈希、clean 分母一致；4B/9B 各自原始、一轮、三轮的逐题身份一致；训练和评测拒绝或截断记录为 0。",
              ""]
    output = HERE / "scaling_and_continuation_summary.md"
    output.write_text("\n".join(lines) + "\n")
    print(output)


if __name__ == "__main__":
    main()
