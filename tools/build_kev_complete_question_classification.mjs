import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = "/Users/chen/Documents/ChatGPT/procogs";
const evalRoot = `${root}/third_party/kev-source-20261025/evals`;
const outputDir = `${root}/outputs/kev-question-classification-20261031`;

const sourceMap = {
  hard_tradeoff: ["多约束权衡决策", "否", ""],
  hard_probability: ["概率", "是", "概率"],
  hard_temporal_numeric: ["时间与数值", "是", "时间与数值"],
  hard_multi_hop: ["多跳推理", "是", "多跳推理"],
  hard_judge: ["计算结果核验", "否", ""],
  hard_long_policy: ["长政策", "是", "长政策"],
  hard_ambiguous: ["信息不足", "是", "信息不足"],
  commitpackft: ["代码变更理解", "否", ""],
  codereviewer: ["代码审查", "否", ""],
  aegis: ["安全风险判断", "否", ""],
  flakeflagger: ["测试稳定性判断", "否", ""],
  when2call: ["工具路由", "是", "工具路由"],
  prompt_injection: ["提示注入", "是", "提示注入"],
};

const descriptions = {
  hard_tradeoff: "在满足硬约束的候选项中，按成本、优先级或加权规则选择方案，并判断指定方案是否满足约束。",
  hard_probability: "计算条件概率、独立事件概率、概率表、概率比较或期望收益。",
  hard_temporal_numeric: "计算日期差、截止时间、时区、按比例退款、轮班工资或周期性日期。",
  hard_multi_hop: "沿依赖、组织、值班或所有权关系连续推理。",
  hard_judge: "复算给定数值或逻辑结论，并判断结果是否正确。",
  hard_long_policy: "阅读较长政策，判断处理结果并计算金额。",
  hard_ambiguous: "判断已给事实能否唯一确定答案；事实不足时选择无法确定。",
  commitpackft: "识别代码变更类型，并判断提交说明是否与差异内容一致。",
  codereviewer: "判断代码改动是否需要审查意见。",
  aegis: "判断内容是否不安全；部分题还要求选择风险类别。",
  flakeflagger: "判断测试失败是否属于不稳定测试。",
  when2call: "根据任务、可用工具和参数完整性选择下一步动作。",
  prompt_injection: "识别网页、邮件、工具输出等内容中的提示注入。",
};

const subtypeZh = {
  lex: "按优先级排序", weighted: "加权评分", tco: "总拥有成本",
  bayes: "贝叶斯反推", compare: "概率比较", ev: "期望收益", independent: "独立事件", table: "频数表",
  deadline: "截止时间", diff: "日期差", prorata: "按比例退款", shift: "轮班工资", tz: "时区换算",
  recurring_business_days: "工作日周期", recurring_every_n_weeks: "每N周周期", recurring_last_business: "月末最后工作日", recurring_monthly_rollback: "月度日期回退",
  deps: "依赖传播", oncall: "值班查询", org: "组织审批", ownership: "控制权与经济权益",
  convert: "单位换算核验", fence: "边界条件核验", logic: "逻辑核验", order: "运算顺序核验", pct_change: "百分比变化核验", rate: "比率核验", reverse_pct: "反向百分比核验", wavg: "加权平均核验",
  benefits: "福利政策", device: "设备保障", home: "家庭保障", travel: "旅行保障",
  approval: "审批", overtime: "加班", price_match: "价格匹配", return_window: "退货期限", shipping: "配送", tenure: "任职年限", warranty: "保修",
};

function readJsonl(text) {
  return text.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}
function compact(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}
function labelText(q) {
  const label = q.label;
  if (q.criteria && typeof q.criteria === "object" && !Array.isArray(q.criteria)) {
    const shown = q.criteria[String(label)];
    if (shown !== undefined && shown !== null) return `${String(label)}：${compact(shown)}`;
  }
  return compact(label);
}
function criteriaText(q) {
  if (!q.criteria) return "";
  if (Array.isArray(q.criteria)) return q.criteria.map((x, i) => `${i}: ${compact(x)}`).join(" | ");
  return Object.entries(q.criteria).map(([k, v]) => `${k}: ${v === null ? k : compact(v)}`).join(" | ");
}

const detail = [];
const contextCounts = {};
let contextOrdinal = 0;
for (const suite of ["hard-v1", "devtools-v1"]) {
  const records = readJsonl(await fs.readFile(`${evalRoot}/${suite}/test.jsonl`, "utf8"));
  for (const record of records) {
    contextOrdinal += 1;
    const meta = record._meta || {};
    const id = meta.id || "";
    const duplicateKey = `${suite}\u0000${id}`;
    contextCounts[duplicateKey] = (contextCounts[duplicateKey] || 0) + 1;
    const occurrence = contextCounts[duplicateKey];
    const source = meta.source || "";
    if (!sourceMap[source]) throw new Error(`Unmapped source: ${source}`);
    const [category, target, targetCategory] = sourceMap[source];
    let qOrdinal = 0;
    for (const [qName, q] of Object.entries(record.questions || {})) {
      qOrdinal += 1;
      detail.push([
        detail.length + 1,
        suite,
        contextOrdinal,
        id,
        occurrence,
        qOrdinal,
        qName,
        source,
        category,
        meta.subtype || "",
        subtypeZh[meta.subtype] || "",
        target,
        targetCategory,
        q.type || "",
        q.instructions || "",
        labelText(q),
        criteriaText(q),
        meta.group_id || "",
        meta.template || "",
        typeof record.state === "string" ? record.state : JSON.stringify(record.state),
      ]);
    }
  }
}

if (detail.length !== 2161) throw new Error(`Expected 2161 questions, got ${detail.length}`);
const targetCount = detail.filter((r) => r[11] === "是").length;
if (targetCount !== 1000) throw new Error(`Expected 1000 v6 target questions, got ${targetCount}`);
const duplicateContextIds = Object.values(contextCounts).filter((n) => n > 1).length;
if (duplicateContextIds !== 1) throw new Error(`Expected one repeated context ID, got ${duplicateContextIds}`);

const workbook = Workbook.create();
const summary = workbook.worksheets.add("分类汇总");
const taxonomy = workbook.worksheets.add("分类说明");
const questions = workbook.worksheets.add("全部题目");
summary.showGridLines = false;
taxonomy.showGridLines = false;
questions.showGridLines = false;
summary.tabColor = "#1F4E78";
taxonomy.tabColor = "#5B9BD5";
questions.tabColor = "#A5A5A5";

const headers = ["序号","数据集","情境序号","情境ID","同ID出现序号","情境内子问序号","子问题名","原始source","中文大类","原始subtype","subtype中文","是否v6七类","v6目标大类","题型","问题要求","正确标签","候选项","group_id","模板","完整题面"];
questions.getRange("A1:T1").values = [headers];
questions.getRangeByIndexes(1, 0, detail.length, headers.length).values = detail;
const detailTable = questions.tables.add(`A1:T${detail.length + 1}`, true, "AllQuestionsTable");
detailTable.style = "TableStyleMedium2";
detailTable.showFilterButton = true;
detailTable.showBandedRows = true;
questions.freezePanes.freezeRows(1);
questions.freezePanes.freezeColumns(4);
questions.getRange("A1:T1").format = {fill:"#1F4E78",font:{bold:true,color:"#FFFFFF"},verticalAlignment:"center",wrapText:true,borders:{preset:"all",style:"thin",color:"#D9E2F3"}};
questions.getRange(`A2:T${detail.length + 1}`).format = {verticalAlignment:"top",borders:{preset:"all",style:"thin",color:"#E7E6E6"}};
questions.getRange(`A2:A${detail.length + 1}`).setNumberFormat("0");
questions.getRange(`C2:F${detail.length + 1}`).setNumberFormat("0");
questions.getRange(`O2:T${detail.length + 1}`).format.wrapText = true;
questions.getRange(`A1:T${detail.length + 1}`).format.font = {name:"Arial",size:10,color:"#000000"};
questions.getRange("A:A").format.columnWidth = 8;
questions.getRange("B:B").format.columnWidth = 13;
questions.getRange("C:C").format.columnWidth = 10;
questions.getRange("D:D").format.columnWidth = 31;
questions.getRange("E:F").format.columnWidth = 11;
questions.getRange("G:G").format.columnWidth = 18;
questions.getRange("H:H").format.columnWidth = 22;
questions.getRange("I:I").format.columnWidth = 18;
questions.getRange("J:J").format.columnWidth = 24;
questions.getRange("K:K").format.columnWidth = 18;
questions.getRange("L:L").format.columnWidth = 12;
questions.getRange("M:M").format.columnWidth = 16;
questions.getRange("N:N").format.columnWidth = 10;
questions.getRange("O:O").format.columnWidth = 42;
questions.getRange("P:P").format.columnWidth = 28;
questions.getRange("Q:Q").format.columnWidth = 55;
questions.getRange("R:R").format.columnWidth = 32;
questions.getRange("S:S").format.columnWidth = 24;
questions.getRange("T:T").format.columnWidth = 70;
questions.getRange(`A2:T${detail.length + 1}`).format.rowHeight = 36;
questions.getRange("A1:T1").format.rowHeight = 32;
questions.getRange(`L2:L${detail.length + 1}`).conditionalFormats.add("containsText", {text:"是",format:{fill:"#E2F0D9",font:{bold:true,color:"#375623"}}});

const taxonomyRows = Object.entries(sourceMap).map(([source, [category, target, targetCategory]]) => {
  const matching = detail.filter((r) => r[7] === source);
  const subtypeList = [...new Set(matching.map((r) => r[9]).filter(Boolean))].sort().join("、");
  const qList = [...new Set(matching.map((r) => r[6]))].sort().join("、");
  return [source, category, target, targetCategory, matching.length, subtypeList, qList, descriptions[source]];
});
taxonomy.getRange("A1:H1").values = [["原始source","中文大类","是否v6七类","v6目标大类","子问数","原始subtype","子问题名","分类含义"]];
taxonomy.getRangeByIndexes(1,0,taxonomyRows.length,8).values = taxonomyRows;
taxonomy.tables.add(`A1:H${taxonomyRows.length+1}`,true,"TaxonomyTable").style="TableStyleMedium2";
taxonomy.freezePanes.freezeRows(1);
taxonomy.getRange(`A1:H${taxonomyRows.length+1}`).format = {font:{name:"Arial",size:10,color:"#000000"},verticalAlignment:"top",wrapText:true,borders:{preset:"all",style:"thin",color:"#D9D9D9"}};
taxonomy.getRange("A1:H1").format = {fill:"#1F4E78",font:{name:"Arial",size:10,bold:true,color:"#FFFFFF"},verticalAlignment:"center",wrapText:true,borders:{preset:"all",style:"thin",color:"#D9E2F3"}};
for (const [col,width] of [["A:A",24],["B:B",20],["C:C",14],["D:D",18],["E:E",10],["F:F",38],["G:G",28],["H:H",68]]) taxonomy.getRange(col).format.columnWidth=width;
taxonomy.getRange(`A2:H${taxonomyRows.length+1}`).format.rowHeight=48;
taxonomy.getRange("A1:H1").format.rowHeight=30;

summary.getRange("A1:F1").merge();
summary.getRange("A1").values = [["Kev hard-v1 与 devtools-v1 完整题目分类"]];
summary.getRange("A2:F2").merge();
summary.getRange("A2").values = [["按冻结 test.jsonl 展开到每个子问；保留原始 source 和 subtype，并标出 v6 七类目标子集"]];
summary.getRange("A4:B8").values = [
  ["指标","数量"],
  ["测试集",2],
  ["情境记录",1600],
  ["子问总数",2161],
  ["v6 七类目标子问",1000],
];
summary.getRange("A10:F10").values = [["原始source","中文大类","子问数","占全部子问","是否v6七类","数据集"]];
const sourceOrder = Object.keys(sourceMap);
for (let i=0;i<sourceOrder.length;i++) {
  const source=sourceOrder[i];
  const [category,target]=sourceMap[source];
  const row=11+i;
  summary.getRange(`A${row}:B${row}`).values=[[source,category]];
  summary.getRange(`C${row}`).formulas=[[`=COUNTIF('全部题目'!$H$2:$H$${detail.length+1},A${row})`]];
  summary.getRange(`D${row}`).formulas=[[`=C${row}/$B$7`]];
  summary.getRange(`E${row}`).values=[[target]];
  summary.getRange(`F${row}`).values=[[source.startsWith("hard_")?"hard-v1":"devtools-v1"]];
}
summary.getRange("A26:F26").values = [["v6目标大类","子问数","占目标子问","hard-v1","devtools-v1","说明"]];
const targetFamilies=["工具路由","时间与数值","概率","信息不足","多跳推理","长政策","提示注入"];
for (let i=0;i<targetFamilies.length;i++) {
  const row=27+i;
  summary.getRange(`A${row}`).values=[[targetFamilies[i]]];
  summary.getRange(`B${row}`).formulas=[[`=COUNTIF('全部题目'!$M$2:$M$${detail.length+1},A${row})`]];
  summary.getRange(`C${row}`).formulas=[[`=B${row}/$B$8`]];
  summary.getRange(`D${row}`).formulas=[[`=COUNTIFS('全部题目'!$M$2:$M$${detail.length+1},A${row},'全部题目'!$B$2:$B$${detail.length+1},"hard-v1")`]];
  summary.getRange(`E${row}`).formulas=[[`=COUNTIFS('全部题目'!$M$2:$M$${detail.length+1},A${row},'全部题目'!$B$2:$B$${detail.length+1},"devtools-v1")`]];
  summary.getRange(`F${row}`).values=[[i<5&&i>0?"hard-v1 目标类":(targetFamilies[i]==="工具路由"||targetFamilies[i]==="提示注入"?"devtools-v1 目标类":"hard-v1 目标类")]];
}
summary.getRange("A36:F38").values = [
  ["口径说明","内容","","","",""],
  ["分类层级","原始 source 是数据集自带一级标签；subtype 和子问题名是更细标签；中文大类是便于阅读的对应名称。","","","",""],
  ["重复 ID","devtools-v1 原始测试中有一组重复情境 ID；全部题目表用“同ID出现序号”保留两次出现，不去重。","","","",""],
];
summary.getRange("B37:F37").merge();summary.getRange("B38:F38").merge();
summary.freezePanes.freezeRows(2);
summary.getRange("A1:F38").format.font={name:"Arial",size:10,color:"#000000"};
summary.getRange("A1:F1").format={fill:"#FFFFFF",font:{name:"Arial",size:18,bold:true,color:"#000000"},verticalAlignment:"center"};
summary.getRange("A2:F2").format={fill:"#FFFFFF",font:{name:"Arial",size:10,color:"#404040"},verticalAlignment:"center"};
for (const row of [4,10,26,36]) summary.getRange(`A${row}:F${row}`).format={fill:"#1F4E78",font:{name:"Arial",size:10,bold:true,color:"#FFFFFF"},verticalAlignment:"center",wrapText:true,borders:{preset:"all",style:"thin",color:"#D9E2F3"}};
for (const range of ["A5:B8","A11:F23","A27:F33","A37:F38"]) summary.getRange(range).format={verticalAlignment:"center",wrapText:true,borders:{preset:"all",style:"thin",color:"#D9D9D9"}};
summary.getRange("D11:D23").setNumberFormat("0.0%");
summary.getRange("C27:C33").setNumberFormat("0.0%");
summary.getRange("A:A").format.columnWidth=27; summary.getRange("B:B").format.columnWidth=22;
summary.getRange("C:C").format.columnWidth=14; summary.getRange("D:E").format.columnWidth=16; summary.getRange("F:F").format.columnWidth=22;
summary.getRange("A1:F1").format.rowHeight=34;summary.getRange("A2:F2").format.rowHeight=26;
summary.getRange("A37:F38").format.rowHeight=42;
summary.getRange("E11:E23").conditionalFormats.add("containsText", {text:"是",format:{fill:"#E2F0D9",font:{bold:true,color:"#375623"}}});

workbook.recalculate();
const summaryCheck = await workbook.inspect({kind:"table",range:"分类汇总!A1:F38",include:"values,formulas",tableMaxRows:40,tableMaxCols:8,maxChars:12000});
console.log(summaryCheck.ndjson);
const taxonomyCheck = await workbook.inspect({kind:"table",range:`分类说明!A1:H${taxonomyRows.length+1}`,include:"values",tableMaxRows:20,tableMaxCols:8,maxChars:12000});
console.log(taxonomyCheck.ndjson);
const detailTop = await workbook.inspect({kind:"table",range:"全部题目!A1:T8",include:"values",tableMaxRows:8,tableMaxCols:20,maxChars:8000});
console.log(detailTop.ndjson);
const errors = await workbook.inspect({kind:"match",searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",options:{useRegex:true,maxResults:300},summary:"final formula error scan"});
console.log(errors.ndjson);

await fs.mkdir(outputDir,{recursive:true});
for (const [sheetName,range,file] of [["分类汇总","A1:F38","preview-summary.png"],["分类说明",`A1:H${taxonomyRows.length+1}`,"preview-taxonomy.png"],["全部题目","A1:T18","preview-detail.png"]]) {
  const blob = await workbook.render({sheetName,range,scale:1.35,format:"png"});
  await fs.writeFile(`${outputDir}/${file}`,new Uint8Array(await blob.arrayBuffer()));
}
const output = await SpreadsheetFile.exportXlsx(workbook);
const outputPath = `${outputDir}/Kev完整题目分类表_hard-v1_devtools-v1.xlsx`;
await output.save(outputPath);
await fs.writeFile(`${outputDir}/build_manifest.json`,JSON.stringify({outputPath,contexts:1600,questions:detail.length,v6TargetQuestions:targetCount,sourceCategories:Object.keys(sourceMap).length,generatedAt:"2026-10-31"},null,2));
console.log(JSON.stringify({outputPath,contexts:1600,questions:detail.length,v6TargetQuestions:targetCount,sourceCategories:Object.keys(sourceMap).length}));
