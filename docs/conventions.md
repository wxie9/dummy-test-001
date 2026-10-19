# 编号与记录规范

## 稳定 ID

格式：`前缀-YYYYMMDD-MEMBER-NNN`。日期为创建记录时的日期，采用 Asia/Shanghai；实际采集或执行日期另填。成员代号见 [成员表](../metadata/members.tsv)，三位序号从 `001` 开始。同一成员、日期、前缀内递增；创建前在仓库搜索完整 ID。

| 对象 | 前缀 | 保存位置与文件名 |
| --- | --- | --- |
| 研究问题 | Q | `research/questions/<ID>.md` |
| 假设 | H | `research/hypotheses/<ID>.md` |
| 决策 | DEC | `research/decisions/<ID>.md` |
| 文献检索 | L | `literature/searches/<ID>.md` |
| 实验方案 | P | `protocols/<ID>/v1.0.0.md` |
| 样本 | S | `metadata/samples.tsv` 中的一行 |
| 湿实验 | E | `experiments/wet/<ID>/record.md` |
| 计算运行 | R | `experiments/computational/<ID>/record.md` |
| 数据集 | D | `metadata/datasets.tsv` 中的一个版本 |

例如 `E-20261019-AA-001` 仅为格式示例，AA 是虚构成员代号，不代表已执行实验。ID 不承载处理条件或实验结果，分配后不改名、不复用。序号超过 999 时延伸为四位数字。

## 文献与方案版本

文献笔记保存为 `literature/notes/<citation-key>.md`。引用键建议为 `FirstAuthorYearKeyword`，仅使用 ASCII 字母、数字、连字符或下划线；创建前按 DOI/PMID 检查是否已有记录。已被引用的键保持稳定；重复条目合并时记录旧键映射。BibTeX 使用同一引用键。

方案通过 `P-…@1.0.0` 引用。新版本另建文件，不覆盖已被实验引用的版本。主版本表示影响研究设计或可比性的变动；次版本表示兼容性扩展；修订版本表示不改变执行含义的勘误。每个版本记清变动原因。

数据集通过 `D-…@v1` 引用。同一版本不可替换内容；变动创建新版本与校验和。原始文件新批次可用新 ID 或新版本，但在登记中说明与旧数据的关系。

## 记录状态与结果

记录状态：`draft`（草稿）、`planned`（待执行）、`in-progress`（进行中）、`completed`（记录已整理完成）、`cancelled`（取消）。文献笔记使用 `draft` / `completed`，检索记录可使用全部状态。`completed` 不代表结果成功或结论成立。

实验/运行结果单独填写：`not-evaluated`、`supports`、`does-not-support`、`inconclusive`、`failed`。无显著差异需结合设计与不确定性解释，不能自动等同于假设被否定。假设证据状态另使用模板中的 `untested`、`supported`、`not-supported`、`mixed`。

模板中的“待填写”需要填写或改为“待确认：原因”；`not-evaluated` 是尚未评估的真实状态。未做的分析写“未执行”，不适用的字段写“不适用：原因”。正式记录不保留无解释的空字段。

## 计算运行与更正

运行前用 `git rev-parse HEAD`、`git status --short` 确认代码版本与工作区状态。优先提交代码和配置后执行；存在未提交修改时，保存包含改动与未跟踪输入的完整快照，并记录定位和校验和。不要只保存无法包含未跟踪文件的 diff 就声称可复现。

运行记录随后提交。其 commit 与执行时的代码 commit 不同是正常情况。相同参数的重跑也新建 `R-…` 编号并关联上次运行。

每次更正追加日期、作者、原内容、改动和依据。新增结果标明获取时间。失败记录保留错误信息、已完成步骤和后续处理，避免只保存成功实验。
