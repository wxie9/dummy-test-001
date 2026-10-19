# 编号与记录规范

## 稳定 ID

格式：`前缀-YYYYMMDD-MEMBER-NNN`。日期为创建记录时的日期，采用 Asia/Shanghai；实际运行时间另填。成员代号见 [成员表](../metadata/members.tsv)，为 2–8 位大写字母或数字。同一成员、日期、前缀内的三位序号从 `001` 递增；创建前搜索完整 ID。超过 999 时延伸为四位序号。

| 对象 | 前缀 | 位置 |
| --- | --- | --- |
| 研究问题 | Q | `research/questions/<ID>.md` |
| 假设 | H | `research/hypotheses/<ID>.md` |
| 决策 | DEC | `research/decisions/<ID>.md` |
| 文献检索 | L | `literature/searches/<ID>.md` |
| 实验计划 | E | `experiments/plans/<ID>.md` |
| 训练运行 | TR | `experiments/training/<ID>/record.md` |
| 评测运行 | EV | `experiments/evaluation/<ID>/record.md` |
| 评测协议 | B | `benchmarks/<ID>/v1.0.0.md` |
| 数据集 | D | `metadata/datasets.tsv` |
| 基础/外部模型 | M | `metadata/models.tsv` |
| 训练 checkpoint | C | `metadata/checkpoints.tsv` |

`TR-20261019-AA-001` 仅是格式示例，AA 是虚构代号，不代表已有训练。ID 不承载模型名称、处理条件或结果，分配后不改名、不复用。一次实验计划可以关联多次 TR 和 EV 运行，重跑分配新运行 ID。

## 文献、协议与数据版本

文献笔记放 `literature/notes/<citation-key>.md`。引用键建议 `FirstAuthorYearKeyword`，仅用 ASCII 字母、数字、连字符或下划线；创建前按 DOI/稳定原文标识检查重复。已被引用的键保持稳定，BibTeX 与笔记使用相同键。

评测协议用 `B-…@1.0.0` 引用。新版本另建文件，不覆盖已被运行引用的版本。影响结果可比性的调整递增主版本；兼容性扩展递增次版本；不改变计分含义的勘误递增修订版本。变更说明写清分数能否直接比较。

数据集用 `D-…@v1:train`、`D-…@v1:validation` 或 `D-…@v1:test` 引用，自定义 split 明确含义。数据集表以 `(dataset_id, version, split)` 唯一。相同版本和 split 的内容不替换，筛选、去重或分割变化产生新版本与校验和。

模型 M-ID 对应不可变的来源 revision；优先记录完整 commit hash，不能仅用会变动的 `main` 或模型名称。C-ID 对应某次训练的固定 step 产物，适配器同时关联基础模型 M-ID。相同文件替换内容时新建 C-ID。

## 状态与结果

状态：`draft`、`planned`、`in-progress`、`completed`、`cancelled`。文献笔记使用 draft/completed。completed 表示本次记录已整理完成，失败运行也可以 completed。

结果另填：`not-evaluated`、`supports`、`does-not-support`、`inconclusive`、`failed`。运行结束不自动意味着能力提升；单独的训练 loss 下降不能替代目标评测。假设证据状态使用模板中的 untested/supported/not-supported/mixed。

“待填写”替换为实际信息，或“待确认：原因”；未执行写“未执行”，不适用注明原因。没有执行时，不填成功退出码、训练消耗或评测分数。

## 执行时代码与更正

运行前用 `git rev-parse HEAD` 和 `git status --short` 确认代码 commit 与工作区状态。优先提交代码和配置后执行；若 dirty，保存包含未跟踪代码/配置的完整快照并登记 URI 和 SHA-256。单独 diff 不包含未跟踪文件，不能据此声称代码已完整归档。

日志稍后提交是正常情况，其提交 hash 不替代运行时 commit。保存实际生效配置和命令行覆盖；恢复训练关联源 checkpoint、step、优化器/调度器/RNG 状态与数据游标，并新建 TR-ID。

更正追加日期、作者、原内容、改动和依据。评测条件、失败条目处理或判断标准事后变化时标明时间与影响，避免只保存最终较好的分数。
