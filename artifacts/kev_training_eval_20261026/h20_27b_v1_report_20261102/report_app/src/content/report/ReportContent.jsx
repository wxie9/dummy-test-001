import React from "react";

import {
  ChartRenderer,
  DataComponent,
  DataTable,
  MetricCard,
  ReportSection,
  RichNarrative,
  useDataApp,
} from "../../data-app-public.jsx";

const pct = (value) => Number.isFinite(value) ? `${(value * 100).toFixed(2)}%` : "—";
const pp = (value) => Number.isFinite(value) ? `${value >= 0 ? "+" : ""}${value.toFixed(2)} pp` : "—";

const suiteChart = {
  type: "bar",
  x: "suite",
  y: "Kev-27B v1 (%)",
  fields: ["Kev-27B v1 (%)", "Kev-9B stage3 (%)", "Kev-4B stage4 (%)"],
  stackable: false,
  valueDecimals: 1,
  yTickCount: 5,
  xLabel: "冻结测试集",
  yLabel: "准确率（%）",
};

function Narrative({ id, value, className = "report-analysis", label = "编辑报告文字" }) {
  return <RichNarrative id={id} value={value} className={className} label={label} />;
}

export function ReportContent() {
  const {
    reviewedRows,
    chartOverrides,
    chartProps,
    visible,
    canEdit,
    mode,
    appTitle,
    setAppTitle,
  } = useDataApp();

  const [training = {}] = reviewedRows("training_summary");
  const suiteRows = reviewedRows("six_suite_results");
  const officialV1 = reviewedRows("official_v1_comparison");
  const officialV2 = reviewedRows("official_v2_comparison");

  const suiteDisplay = suiteRows.map((row) => ({
    suite: row.suite,
    n: row.n,
    correct: row.correct,
    "Kev-27B v1 (%)": Number((row.accuracy * 100).toFixed(2)),
    "Kev-9B stage3 (%)": Number((row.model9B * 100).toFixed(2)),
    "Kev-4B stage4 (%)": Number((row.model4B * 100).toFixed(2)),
    "27B−9B (pp)": Number(((row.accuracy - row.model9B) * 100).toFixed(2)),
  }));
  const officialV1Display = officialV1.map((row) => ({
    panel: row.panel,
    "本次复现 (%)": Number((row.ours * 100).toFixed(2)),
    "官方 v1 (%)": Number((row.official * 100).toFixed(2)),
    "差值 (pp)": Number(((row.ours - row.official) * 100).toFixed(2)),
  }));
  const officialV2Display = officialV2.map((row) => ({
    panel: row.panel,
    "本次 v1 (%)": Number((row.ours * 100).toFixed(2)),
    "官方 v2 (%)": Number((row.official * 100).toFixed(2)),
    "差值 (pp)": Number(((row.ours - row.official) * 100).toFixed(2)),
  }));
  const chart = chartOverrides["kev-suite-chart"] ?? suiteChart;
  const wallHours = Number.isFinite(training.wallSeconds) ? training.wallSeconds / 3600 : 0;
  const clippedRate = training.optimizerSteps ? training.clippedSteps / training.optimizerSteps : 0;

  return <article className="report-content" aria-label="Kev-27B v1 训练与评测报告">
    <header className="report-hero">
      <p className="report-kicker">H20 · 6×GPU · LoRA · 2026-11-01</p>
      <h1 data-data-app-title contentEditable={canEdit && mode === "edit"} suppressContentEditableWarning
        aria-label={canEdit && mode === "edit" ? "编辑报告标题" : undefined}
        onBlur={canEdit && mode === "edit" ? (event) => setAppTitle(event.currentTarget.textContent.trim() || appTitle) : undefined}
        onKeyDown={canEdit && mode === "edit" ? (event) => {
          if (event.key === "Enter") { event.preventDefault(); event.currentTarget.blur(); }
        } : undefined}>{appTitle}</h1>
      <Narrative id="report:introduction" className="report-deck"
        value="复现官方 Kev-27B v1 路线：在 Qwen3.8-27B@1d4bf0f2 上，用官方 B1-v2 数据完成一轮六卡 LoRA 训练，并在六套冻结测试及官方可对齐面板上核验结果。" />
    </header>

    {visible("report-summary") && <ReportSection id="report-summary" title="结论摘要"
      queryIds={["training_summary", "six_suite_results", "official_v1_comparison"]}
      queryId="six_suite_results" sourceRowsByQuery={{
        training_summary: [training], six_suite_results: suiteRows, official_v1_comparison: officialV1,
      }} showHeading={false} className="report-summary">
      <Narrative id="report-summary:body" className="report-summary-lead"
        value={`## 结论摘要\n\n训练完整结束，共 ${training.optimizerSteps?.toLocaleString() ?? "—"} 个 optimizer steps，用时 ${wallHours.toFixed(2)} 小时；原始 15,401 条记录经 none-pair 增广后实际看见 ${training.recordsSeen?.toLocaleString() ?? "—"} 条，拒绝和截断均为 0。六套冻结测试原始加权准确率为 **82.33%**（4,939/5,999）；与官方 v1 可严格对齐的 hard + audited devtools + documents 汇总为 **81.40%**，高于官方 v1 的 80.00%（+1.40 pp）。这说明本次复现总体达到官方 v1 水平，但还没有达到官方 v2：差距集中在 hard、devtools 和 documents，而不是 transfer。`} />
    </ReportSection>}

    <div className="report-facts" aria-label="关键指标">
      <MetricCard id="metric-wall" title="训练时长" queryId="training_summary" sourceRows={[training]}
        value="3:59:48" comparison="正式六卡训练" description="从训练开始到 adapter 保存完成的 wall-clock 时间。" />
      <MetricCard id="metric-steps" title="Optimizer steps" queryId="training_summary" sourceRows={[training]}
        value={training.optimizerSteps?.toLocaleString() ?? "—"} comparison="1 epoch" description="15,401 条官方 B1-v2 数据，world=6、batch=1、accum=1。" />
      <MetricCard id="metric-six-suite" title="六套加权准确率" queryId="six_suite_results" sourceRows={suiteRows}
        value="82.33%" comparison="4,939 / 5,999" description="六套冻结测试的逐题加权结果；重复题调整后为 82.32%。" />
      <MetricCard id="metric-official" title="对齐官方 v1" queryId="official_v1_comparison" sourceRows={officialV1}
        value="+1.40 pp" comparison="81.40% vs 80.00%" deltaTone="positive"
        description="hard、audited devtools 与 documents 的同口径 pooled accuracy。" />
    </div>

    {visible("report-training") && <section className="report-section">
      <ReportSection id="report-training" title="训练结果" queryId="training_summary" sourceRows={[training]} showHeading={false}>
        <Narrative id="report-training:body"
          value={`## 训练结果\n\n本次使用 LoRA rank 16 覆盖全部目标模块，bf16、学习率 5e-5、max state 7,552、seed 2。训练共处理 ${training.forwardTokens?.toLocaleString() ?? "—"} 个 forward tokens，单卡峰值显存约 73.9 GiB。梯度范数均值 ${training.gradientNormMean?.toFixed(2) ?? "—"}、最大值 ${training.gradientNormMax?.toFixed(2) ?? "—"}；${pct(clippedRate)} 的 step 触发裁剪。虽然训练无 NaN、无拒绝、无截断，但高裁剪率应作为复现风险保留，不能把训练完成等同于优化过程完全稳定。`} />
      </ReportSection>
      <div className="training-spec" aria-label="训练配方">
        <div><span>基座</span><strong>Qwen3.8-27B</strong></div>
        <div><span>数据</span><strong>B1-v2 · 15,401</strong></div>
        <div><span>方法</span><strong>LoRA r=16</strong></div>
        <div><span>并行</span><strong>6×H20 DDP</strong></div>
        <div><span>有效 batch</span><strong>6</strong></div>
        <div><span>数据质量</span><strong>0 reject / 0 trunc</strong></div>
      </div>
    </section>}

    {visible("report-six-suite") && <section className="report-section">
      <ReportSection id="report-six-suite" title="六套冻结测试" queryId="six_suite_results" sourceRows={suiteRows} showHeading={false}>
        <Narrative id="report-six-suite:body"
          value="## 六套冻结测试\n\n27B 在 decision、transfer-v4、transfer-v9 上优于先前 9B stage 3，分别提升 +0.58、+1.98、+4.02 pp；但在 hard、devtools、documents 上分别下降 −5.61、−10.53、−2.88 pp。模型规模扩大没有带来一致的 scaling：v1 的 B1-v2 训练分布更偏向 decision/transfer，而我们此前 4B/9B 检查点接受过不同的多阶段或定向训练，因此这不是纯参数规模对比。" />
      </ReportSection>
      <DataComponent id="kev-suite-chart" title="六套测试：27B 与既有 4B/9B 检查点" queryId="six_suite_results"
        kind="chart" chart={chart} displayRows={suiteDisplay} sourceRows={suiteRows}
        description="同一冻结测试集上的逐题准确率；检查点训练路线不同，图中差异不应解释为纯 scaling。">
        <ChartRenderer spec={chart} rows={suiteDisplay} height={360} {...chartProps("kev-suite-chart")} />
      </DataComponent>
      <DataComponent id="kev-suite-table" title="逐套准确率与 27B−9B 差值" queryId="six_suite_results"
        kind="table" displayRows={suiteDisplay} sourceRows={suiteRows}>
        <DataTable rows={suiteDisplay} searchable={false} compactNumbers={false} signedDeltas
          columns={[
            { field: "suite", label: "测试集" },
            { field: "n", label: "题数" },
            { field: "correct", label: "27B 正确" },
            { field: "Kev-27B v1 (%)", label: "27B v1 (%)" },
            { field: "Kev-9B stage3 (%)", label: "9B stage3 (%)" },
            { field: "Kev-4B stage4 (%)", label: "4B stage4 (%)" },
            { field: "27B−9B (pp)", label: "27B−9B (pp)", deltaTone: (value) => value > 0 ? "positive" : value < 0 ? "negative" : "neutral" },
          ]} />
      </DataComponent>
    </section>}

    {visible("report-official-v1") && <section className="report-section">
      <ReportSection id="report-official-v1" title="与官方 Kev-27B v1 对齐" queryId="official_v1_comparison"
        sourceRows={officialV1} showHeading={false}>
        <Narrative id="report-official-v1:body"
          value="## 与官方 Kev-27B v1 对齐\n\n在同口径面板上，本次复现与官方 v1 基本一致：decision +0.25 pp、transfer-v4 −0.91 pp、hard +3.04 pp、audited devtools −0.17 pp、documents +0.71 pp。最有代表性的三套 pooled 指标为 81.40%，高于官方 80.00%。transfer-v9 没有官方同口径公开值，因此不进入官方差值判断。" />
      </ReportSection>
      <DataComponent id="official-v1-table" title="官方 v1 同口径比较" queryId="official_v1_comparison"
        kind="table" displayRows={officialV1Display} sourceRows={officialV1}>
        <DataTable rows={officialV1Display} searchable={false} compactNumbers={false} signedDeltas columns={[
          { field: "panel", label: "面板" },
          { field: "本次复现 (%)" },
          { field: "官方 v1 (%)" },
          { field: "差值 (pp)", deltaTone: (value) => value > 0 ? "positive" : value < 0 ? "negative" : "neutral" },
        ]} />
      </DataComponent>
    </section>}

    {visible("report-official-v2") && <section className="report-section">
      <ReportSection id="report-official-v2" title="与官方 Kev-27B v2 的差距" queryId="official_v2_comparison"
        sourceRows={officialV2} showHeading={false}>
        <Narrative id="report-official-v2:body"
          value="## 与官方 Kev-27B v2 的差距\n\n本次 v1 在 transfer-v4 上仅落后官方 v2 0.15 pp，但在 hard、audited devtools、documents 上分别落后 13.86、3.77、3.19 pp，三套 pooled 低 7.50 pp。这个模式支持一个明确判断：v2 的主要收益来自面向 hard/devtools/documents 等任务族的更广覆盖全参 SFT，而不是只把 v1 的 LoRA 多跑几轮。" />
      </ReportSection>
      <DataComponent id="official-v2-table" title="本次 v1 与官方 v2 同口径比较" queryId="official_v2_comparison"
        kind="table" displayRows={officialV2Display} sourceRows={officialV2}>
        <DataTable rows={officialV2Display} searchable={false} compactNumbers={false} signedDeltas columns={[
          { field: "panel", label: "面板" },
          { field: "本次 v1 (%)" },
          { field: "官方 v2 (%)" },
          { field: "差值 (pp)", deltaTone: (value) => value > 0 ? "positive" : value < 0 ? "negative" : "neutral" },
        ]} />
      </DataComponent>
    </section>}

    <section className="report-section report-sources">
      <Narrative id="report-limitations:body" className="report-caveat"
        value={`## 解释边界\n\n- 六套总分 82.33% 是我们自定义冻结套件的加权结果，不是官方统一 leaderboard 分数。\n- devtools 原始汇总含 2 个重复题；官方口径去重后为 756/1,071（70.59%），六套调整后为 4,937/5,997（82.32%）。\n- 4B、9B、27B 的训练路线和数据覆盖不同，跨规模差异不能直接归因于参数量。\n- 梯度裁剪触发 ${pct(clippedRate)}，虽然没有造成训练失败，但后续若改学习率、batch 或全参训练，必须重新做稳定性验证。`} />
      <Narrative id="report-sources:body" className="report-disclosure"
        value="来源：本次正式训练的 training_metrics.json、六套冻结评测 summary.json 与逐题 rows；官方比较来自 Hugging Face 上 Kev-27B v1-lora 与 main 模型卡。证据截止日期：2026-11-02。" />
    </section>
  </article>;
}
