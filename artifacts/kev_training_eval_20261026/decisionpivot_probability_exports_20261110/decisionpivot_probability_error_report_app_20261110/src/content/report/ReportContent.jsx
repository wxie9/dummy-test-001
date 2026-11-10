import React from "react";

import {
  DataComponent, DataTable, MetricCard, ReportSection, RichNarrative, useDataApp,
} from "../../data-app-public.jsx";

const pct = (value) => `${(Number(value) * 100).toFixed(1)}%`;
const familyNames = {
  triage_order: "分诊排序",
  ledger_reconcile: "账本核对",
  sched_conflict: "排期冲突",
  filter_match: "条件筛选",
  dep_resolve: "依赖解析",
  policy_case: "政策判断",
  perm_inherit: "权限继承",
  state_goal: "状态目标",
  record_rule: "记录规则",
  answerable_facts: "信息完整性",
  log_count_check: "日志计数",
  clause_change: "条款变化",
  toolcall_valid: "工具调用校验",
};

export function ReportContent() {
  const { reviewedPeriodRows, visible, canEdit, mode, appTitle, setAppTitle } = useDataApp();
  const overall = reviewedPeriodRows("overall");
  const thresholds = reviewedPeriodRows("threshold-sensitivity");
  const families = reviewedPeriodRows("family-large-errors");
  const levels = reviewedPeriodRows("level-large-errors");
  const directions = reviewedPeriodRows("direction-large-errors");

  const familyDisplay = families.map((row) => ({
    任务族: familyNames[row.task] ?? row.task,
    大错题数: row.large_errors,
    大错率: row.large_error_rate_all,
    gold第3名以后: row.gold_rank_3plus,
  }));
  const thresholdDisplay = thresholds.map((row) => ({
    "rank2 gap阈值": row.threshold,
    大错题数: row.large_errors,
    占错题: row.share_wrong,
    占全部题: row.share_all,
  }));
  const levelDisplay = levels.map((row) => ({
    难度层: `Level ${row.level}`,
    全部题: row.n,
    错题: row.errors,
    大错: row.large_errors,
    大错率: row.large_error_rate_all,
    占全部大错: row.share_of_all_large_errors,
  }));
  const directionDisplay = directions.map((row) => ({
    任务族: familyNames[row.task] ?? row.task,
    gold方向: row.gold,
    样本数: row.n,
    大错题数: row.large_errors,
    大错率: row.large_error_rate_all,
  }));

  return <article className="report-content" aria-label="DecisionPivot probability error report">
    <header className="report-hero">
      <p className="report-kicker">DecisionPivot · 7,800题 · Kev-27B融合版</p>
      <h1 data-data-app-title contentEditable={canEdit && mode === "edit"} suppressContentEditableWarning
        onBlur={canEdit && mode === "edit" ? (event) => setAppTitle(event.currentTarget.textContent.trim() || appTitle) : undefined}
        onKeyDown={canEdit && mode === "edit" ? (event) => {
          if (event.key === "Enter") { event.preventDefault(); event.currentTarget.blur(); }
        } : undefined}>{appTitle}</h1>
      <RichNarrative id="report:intro" className="report-deck" label="编辑报告导语"
        value="把答错拆成两件事：**正确答案排第几**，以及**错误首选比正确答案高多少概率**。这样可以区分真正的近失误、稳定偏向错误答案，以及多选项任务中的候选定位失败。" />
    </header>

    <div className="report-facts" aria-label="关键统计">
      {visible("metric-wrong") && <MetricCard id="metric-wrong" title="全部错题" queryId="overall"
        sourceRows={overall} value="2,253" description="占7,800题的28.88%。" />}
      {visible("metric-large") && <MetricCard id="metric-large" title="大错" queryId="overall"
        sourceRows={overall} value="1,709" description="占错题75.85%，占全部题21.91%。" />}
      {visible("metric-rank3") && <MetricCard id="metric-rank3" title="gold第3名以后" queryId="overall"
        sourceRows={overall} value="499" description="正确答案已不在第二候选位置。" />}
      {visible("metric-sl") && <MetricCard id="metric-sl" title="StartLux可纠正" queryId="overall"
        sourceRows={overall} value="94.85%" description="在1,709道Kev大错上的交叉检查。" />}
    </div>

    <ReportSection id="report-method" title="统计过程" queryId="overall" sourceRows={overall} showHeading={false}>
      <RichNarrative id="report-method:body" className="report-analysis" label="编辑统计过程"
        value={`## 统计过程

1. 用 \`item_id + question_id\` 对齐Kev、StartLux Instant、AutoThink和原题，要求三模型均覆盖7,800题。
2. 校验概率范围、概率和、\`choice = argmax(probability)\`，并读取gold、选项数、Level和生成元数据。
3. 每题计算 \`pmax\`、\`p_gold\`、\`gold_rank\`、top1–top2 margin和 \`gold_gap = pmax - p_gold\`。
4. 先做六状态审计：稳定/中等/脆弱正确，近失误/高置信/其他错误。
5. 再按指定口径重分：错题中，**gold不是第2名，或gold第2但gap>0.30，定义为大错**；其余为小错。
6. 用任务族、Level、答案方向、45个重叠细类、元数据子组和StartLux对照定位错误模式。
7. 把“直接观察”“有统计支持的行为机制”“已确认训练根因”分开写，避免把相关性当因果。`} />
    </ReportSection>

    <ReportSection id="report-definition" title="为什么不能只看confidence" queryId="overall" sourceRows={overall} showHeading={false}>
      <RichNarrative id="report-definition:body" className="report-analysis" label="编辑概率定义"
        value={`## 为什么不能只看confidence

多选题里，top1置信度只说明模型有多相信首选，不说明正确答案排第2还是第6。答错时必须同时看 \`gold_rank\` 和 \`gold_gap\`；答对时才用top1–top2 margin判断是否稳定。若gold已掉到第3名以后，两个错误选项之间即便很接近，也不能算“只差一点”。`} />
    </ReportSection>

    <DataComponent id="threshold-table" title="0.30阈值不是唯一答案：敏感性检查" queryId="threshold-sensitivity"
      kind="table" displayRows={thresholdDisplay} sourceRows={thresholds}
      description="gold第3名以后始终算大错，只改变gold第2时的概率差阈值。">
      <DataTable rows={thresholdDisplay} searchable={false} caption="大错阈值敏感性"
        columns={[
          { field: "rank2 gap阈值", label: "rank2 gap阈值", renderCell: (value) => Number(value).toFixed(2) },
          { field: "大错题数" },
          { field: "占错题", renderCell: (value) => pct(value) },
          { field: "占全部题", renderCell: (value) => pct(value) },
        ]} />
    </DataComponent>

    <DataComponent id="family-table" title="大错首先集中在五个任务族" queryId="family-large-errors"
      kind="table" displayRows={familyDisplay} sourceRows={families}
      description="分诊、账本、排期、筛选和依赖合计1,021题，占全部大错59.74%。">
      <DataTable rows={familyDisplay} caption="13任务族大错统计" rowKey="任务族"
        columns={[
          { field: "任务族", presentation: "identity" },
          { field: "大错题数", presentation: "bar", max: 300 },
          { field: "大错率", renderCell: (value) => pct(value) },
          { field: "gold第3名以后" },
        ]} />
    </DataComponent>

    <DataComponent id="level-table" title="复杂度上升时，大错率同步上升" queryId="level-large-errors"
      kind="table" displayRows={levelDisplay} sourceRows={levels}
      description="Level 2–3合计1,452道大错，占全部大错84.96%。">
      <DataTable rows={levelDisplay} searchable={false} caption="Level大错统计"
        columns={[
          { field: "难度层", presentation: "identity" },
          { field: "全部题" }, { field: "错题" }, { field: "大错" },
          { field: "大错率", renderCell: (value) => pct(value) },
          { field: "占全部大错", renderCell: (value) => pct(value) },
        ]} />
    </DataComponent>

    <DataComponent id="direction-table" title="答案方向揭示默认偏置" queryId="direction-large-errors"
      kind="table" displayRows={directionDisplay} sourceRows={directions}
      description="排期、筛选、依赖的合法正例更容易被拒绝；状态目标和信息完整性更容易在条件不满足时误选yes。">
      <DataTable rows={directionDisplay} caption="二元任务方向偏置"
        columns={[
          { field: "任务族", presentation: "identity" },
          { field: "gold方向" }, { field: "样本数" }, { field: "大错题数" },
          { field: "大错率", renderCell: (value) => pct(value) },
        ]} />
    </DataComponent>

    <ReportSection id="report-causes" title="错因如何判断" queryId="family-large-errors"
      queryIds={["family-large-errors", "level-large-errors", "direction-large-errors"]}
      sourceRowsByQuery={{
        "family-large-errors": families,
        "level-large-errors": levels,
        "direction-large-errors": directions,
      }} showHeading={false}>
      <RichNarrative id="report-causes:body" className="report-analysis" label="编辑错因结论"
        value={`## 错因如何判断

- **默认no / 过度拒绝：** 排期、筛选和依赖中，gold=yes的大错率分别为56.0%、43.3%和40.0%，明显高于gold=no。
- **错误yes / 漏查条件：** 状态目标与信息完整性中，gold=no的大错率都比gold=yes高15.3个百分点。
- **多候选定位失败：** 499题的gold排第3名以后；其中分诊225题、账本175题、记录规则56题。
- **复杂规则执行不完整：** Level 1/2/3大错率依次为9.88%、24.23%、31.62%。
- **训练侧已确认问题：** 日志 \`off_by_one\` 生成器训练的是普通计数选择题，与评测要求不一致。其余模式目前是行为诊断，还不是训练因果证明。`} />
    </ReportSection>

    <ReportSection id="report-limits" title="证据边界" queryId="overall" sourceRows={overall} showHeading={false}>
      <RichNarrative id="report-limits:body" className="report-disclosure" label="编辑证据边界"
        value={`## 证据边界

没有保存Kev原始CoT，因此只能分析最终选择、各选项概率、题目结构和跨模型对照。0.30是本轮诊断阈值，不是DecisionPivot官方指标。45细类与元数据子组相互重叠，不能相加。StartLux能做对只能排除大量“题目本身不可解”的解释，不能证明其推理链一定正确。`} />
    </ReportSection>
  </article>;
}
