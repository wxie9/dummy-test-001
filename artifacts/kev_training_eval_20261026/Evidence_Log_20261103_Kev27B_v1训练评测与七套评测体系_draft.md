# Evidence Log — 2026/11/03

Name: Kev-27B v1 六卡训练复现、六套冻结评测与七套评测体系整理

> 状态：本地审阅草稿，尚未同步飞书。

## 1. Last Meeting’s Actions

### 1.1 完成 Kev-27B v1 六卡训练

本轮在 H20 服务器上完成了 Kev-27B v1 六卡训练。使用的训练数据和基座 revision 均与官方 v1 对齐：

| 项目 | 本次配置或结果 |
|---|---|
| 基座 | `Qwen/Qwen3.8-27B` |
| 基座 revision | `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` |
| 训练数据 | 官方 B1-v2 重建数据 |
| requested records | 15,401 |
| 数据 SHA-256 | `fb86543b3baccb5aff9355065821e8481a083b874521637dc2f3a5cb06faa56a` |
| 数据一致性 | 与官方 v1 B1-v2 完全同哈希 |

训练结果：

| 指标 | 结果 |
|---|---:|
| optimizer steps | 2,567 / 2,567 |
| rejected records | 0 |
| truncated records | 0 |
| wall time | 14,387.924 秒，即 3:59:47.9 |

训练完整结束，没有出现 OOM、NaN、数据拒绝或截断。由于本次和官方运行的有效 batch、代码路径并不完全相同，结论应表述为“同数据、同基座的性能层级复现”，不能表述为 bit-for-bit 复现。

### 1.2 完成六套冻结测试

本次 checkpoint 使用与此前 4B/9B 相同的 six-suite manifests 完成评测。共覆盖 5,378 records / 6,565 questions，所有 suite 均为 0 rejected、0 truncated。

普通 clean accuracy 的统一分母为 5,999 个问题。`transfer-v9` 的 110 道 `unknowable` 题用于检查证据不足时的置信度行为，不计普通准确率，因此该套普通准确率分母为 1,046，而不是 1,156。

| 测试集 | 主要能力 | 4B stage4 | 9B stage3 | 27B v1 | 27B−9B |
|---|---|---:|---:|---:|---:|
| decision-v7 | 基础分类、评分、推断与政策决策 | 86.92% | 86.67% | **87.25%**（1047/1200） | +0.58 pp |
| transfer-v4 | 新任务、新标签和规则组合迁移 | 83.99% | 86.74% | **88.72%**（582/656） | +1.98 pp |
| transfer-v9 | 困难知识、干扰文本和信息缺失 | 77.53% | 80.50% | **84.51%**（884/1046） | +4.02 pp |
| hard-v1 | 长政策、多跳、概率、时间数值和约束权衡 | 80.06% | 83.55% | **77.94%**（848/1088） | −5.61 pp |
| devtools-v1 | 工具路由、提示注入、代码和测试判断 | 75.21% | 81.17% | **70.64%**（758/1073） | −10.53 pp |
| documents-v1 | CFPB 金融长文档分类 | 89.32% | 90.49% | **87.61%**（820/936） | −2.88 pp |
| **clean 加权** | 六套普通准确率合计 | **82.00%** | **84.65%** | **82.33%**（4939/5999） | **−2.32 pp** |

按官方 devtools 审计口径剔除重复 ID `codereviewer/cls-test/19245` 的两条记录后：

- devtools-v1：756/1,071 = 70.59%；
- 六套 clean 加权：4,937/5,997 = 82.32%。

### 1.3 与官方 Kev-27B v1 对齐

同口径 panel 的对比如下：

| 同口径 test panel | 官方 v1 | 本次六卡 v1 | 本次−官方 |
|---|---:|---:|---:|
| decision-v7 test | 87.00% | 87.25% | +0.25 pp |
| transfer-v4 locked test | 89.63% | 88.72% | −0.91 pp |
| hard-v1 | 74.90% | 77.94% | +3.04 pp |
| devtools-v1 audited sources | 78.90% | 78.73% | −0.17 pp |
| documents-v1 | 86.90% | 87.61% | +0.71 pp |
| **hard + audited devtools + documents pooled** | **80.00%** | **81.40%** | **+1.40 pp** |
| devtools-v1 all sources | 71.10% | 70.59% | −0.51 pp |

本次 checkpoint 在可直接比较的官方 v1 panel 上没有出现系统性退化：部分 suite 略高，部分略低，整体处于官方 v1 的性能层级。`transfer-v9` 只有官方 development 成绩，没有与本次 1,046 题 test 同口径的官方数字，因此没有放入直接比较。

### 1.4 与官方 Kev-27B v2 对比

| 同口径 test panel | 官方 v2 | 本次 v1 | 本次 v1−v2 |
|---|---:|---:|---:|
| transfer-v4 locked test | 88.87% | 88.72% | −0.15 pp |
| hard-v1 | 91.80% | 77.94% | −13.86 pp |
| devtools-v1 audited sources | 82.50% | 78.73% | −3.77 pp |
| documents-v1 | 90.80% | 87.61% | −3.19 pp |
| **hard + audited devtools + documents pooled** | **88.90%** | **81.40%** | **−7.50 pp** |
| devtools-v1 all sources | 79.00% | 70.59% | −8.41 pp |

v1 与 v2 在 transfer-v4 上基本持平，主要差距集中在 hard、devtools 和 documents。官方 v2 的全参数 SFT 数据显式覆盖了这些训练家族，因此该差距更像训练覆盖差异，而不是本次 v1 训练失败。

### 1.5 整理七套评测数据的构成

七套评测并不是七份同质的准确率测试，它们分别测基础分布、迁移、复杂推理、工具安全、长文档和能力广度。

| 评测集 | Clean records | Questions | 普通准确率分母 | 主要用途 |
|---|---:|---:|---:|---|
| decision-v7 | 960 | 1,200 | 1,200 | 基础分类、评分、推断和政策决策 |
| transfer-v4 | 656 | 656 | 656 | 第一层分布外迁移 |
| transfer-v9 | 1,156 | 1,156 | 1,046 | 困难迁移、干扰文本、信息缺失与置信度 |
| hard-v1 | 700 | 1,088 | 1,088 | 复杂推理压力测试 |
| devtools-v1 | 900 | 1,073 | 1,073 | 工具、代码和安全决策 |
| documents-v1 | 574 | 936 | 936 | 金融长文档分类 |
| breadth-v1 | 1,990 | 3,089 | 3,089 | 综合能力广度测试 |
| **合计** | **6,936** | **9,198** | **9,088** |  |

本次 27B v1 实际完成的是前六套评测；`breadth-v1` 在本轮只完成了官方 manifest 构成整理，尚未获得 27B v1 实测分数。

#### decision-v7

960 records / 1,200 questions。由 AG News、Amazon Reviews、Banking77、BoolQ、政策/组合规则 contrastive、DBpedia14、IMDb、MNLI、SST-5、TREC 和 Yelp 构成，覆盖主题分类、意图分类、情感评分、自然语言推断、是非判断和规则执行。

#### transfer-v4

656 questions。由 composition holdout、contrastive、Emotion、MMLU、PAWS、QNLI、SciQ 和 Tweet Offensive 构成，测试新任务、新标签、知识问答、语义匹配和规则组合迁移。

#### transfer-v9

1,156 questions，其中 1,046 道计普通准确率。除 transfer-v4 的主要任务外，加入 200 道 MMLU-Pro、80 道 buried-state 干扰题、110 道 unknowable 置信度题及 110 道完整证据 control。

#### hard-v1

700 records / 1,088 questions，包含七个原生 family：

1. 信息不足；
2. 答案校验；
3. 长政策；
4. 多跳推理；
5. 概率；
6. 时间与数值；
7. 约束权衡。

这里的原生七类不等于后续弱类续训报告中的业务七类。后者把 hard-v1 与 devtools-v1 重新组合，并加入工具路由和提示注入。

#### devtools-v1

900 records / 1,073 questions。六个来源各有 150 条 record：Aegis 内容安全、CodeReviewer 代码审查、CommitPackFT 变更与提交信息匹配、FlakeFlagger 测试稳定性、Prompt Injection 注入检测、When2Call 工具路由。

#### documents-v1

574 条 CFPB 消费者投诉文本、936 个问题。任务是识别金融产品和投诉主要问题，测试长文档信息抽取及相近标签区分。

#### breadth-v1

1,990 records / 3,089 questions，包含 14 个数据集：MuSR、SATA-Bench、ChessBench、ContractNLI、HellaSwag、CLINC150+OOS、SGD/SGD-X、BRIGHT、BFCL、ToolRet、API-Bank、RouterBench、Humicroedit 和 cfcolor。覆盖多步推理、合同理解、检索、工具调用、模型路由和人类偏好。当前公开仓库只有官方 manifest，没有完整公开 `test.jsonl`。

### 1.6 证据路径

- 训练 checkpoint：`/data/kev/runs/h20-27b-v1-b1v2-ddp6-20261101/`
- 训练证据：`artifacts/kev_training_eval_20261026/h20_27b_v1_6gpu_20261101/`
- 六套评测：`artifacts/kev_training_eval_20261026/h20_27b_v1_six_test_20261102/`
- 完整训练评测报告：`artifacts/kev_training_eval_20261026/h20_27b_v1_report_20261102/Kev-27B_v1训练与评测报告.md`
- 七套评测构成：`artifacts/kev_training_eval_20261026/Kev七套评测数据集构成与任务分类_20261102.md`

## 2. Blockers

1. **尚未完成 breadth-v1 实测。** 当前只有官方 manifest 和任务构成，不能把 3,089 题计入本次 27B v1 的实测总分。
2. **尚未完成 tasksource-heldout-v1。** 因此与官方 v1/v2 的横向指标仍不完整。
3. **不是 bit-for-bit 复现。** 本次运行配置和代码路径与官方并不完全一致。
4. **只有一个 seed。** 当前没有 seed 间方差，0.x–1.x pp 的差异不能被解释为稳定提升。
5. **置信度指标尚不可直比。** 当前评测使用 raw T=1；top-choice accuracy 不受正温度缩放影响，但 Brier/ECE 不能与官方 calibrated checkpoint 直接比较。
6. **4B/9B/27B 不是纯 scaling。** 27B v1 只训练 B1-v2，4B/9B checkpoint 还训练过 skills、devtools 和 documents；模型规模和训练数据同时变化。
7. **官方 v2 比较是外部报告对照，不是本地 v2 复现。** 当前只能说明分数差距集中在哪些能力家族，不能归因到某一个训练机制。

## 3. Decisions / Learnings

1. **本次训练可以认定为成功的 v1 性能层级复现。** 2,567 steps 全部完成，训练和评测 0 rejected/truncated；与官方 v1 的可比 panel 有升有降，三套 pooled 高 1.40 pp，没有系统性失败。
2. **不能把结果写成逐比特官方复现。** 运行配置和代码路径仍有差异，正确表述是“同哈希数据、同基座 revision 的性能层级复现”。
3. **27B v1 的优势集中在基础决策和迁移。** 相对 9B stage3，decision-v7、transfer-v4、transfer-v9 分别提高 0.58、1.98、4.02 pp。
4. **27B v1 在专项能力上弱于多阶段 9B。** hard-v1、devtools-v1、documents-v1 分别低 5.61、10.53、2.88 pp。由于 9B 接受过对应家族训练，这不是“27B 参数更多却更差”的纯规模结论。
5. **v2 的主要增益来自定向覆盖。** v1 与 v2 在 transfer-v4 只差 0.15 pp，但 hard + audited devtools + documents pooled 低 7.50 pp；这与 v2 显式包含这些训练家族一致。
6. **六套加权分数只能作为内部摘要。** 它把基础分布、迁移、复杂推理、工具安全和文档任务混在一起，不是官方单一 headline metric，也不能代替逐 suite 分析。
7. **transfer-v9 必须保留双口径。** 文件中有 1,156 个 clean 问题对象，但普通 accuracy 分母只有 1,046；110 道 unknowable 应单独看置信度行为。
8. **七套评测形成清晰的能力分层。** decision-v7 测基础，transfer-v4/v9 测迁移，hard/devtools/documents 测专项，breadth-v1 测广度。后续新增训练数据时应先说明它对应哪个层次，避免只追一个总分。

## 4. Next Meeting — New Actions

1. **补测 breadth-v1。** 先确认完整可评分数据和官方口径，再报告 27B v1 的总体及 14 个子数据集结果。
2. **补测 tasksource-heldout-v1。** 与官方 v1/v2 的主要横向表对齐。
3. **补测 DecisionPivot Core 1.1。** 使用与 4B/9B 相同的 scoring pipeline，报告 pair accuracy、逐题准确率和 family 分解。
4. **若目标是更严格复现官方 v1，统一运行配置并冻结代码 commit。** 同时至少增加一个 seed，用于判断小幅差异是否稳定。
5. **如果要比较置信度，单独准备不泄漏测试集的 calibration pool。** 拟合温度后再报告 Brier、ECE 和 unknowable/control 差异。
6. **针对 hard/devtools/documents 做 family-level 错误分析。** 优先定位长政策、概率/时间数值、工具路由、提示注入和 CFPB product/issue 的主要错误模式，再决定是否补数据。
7. **v2 路线继续区分“官方复现”和“自定义近似”。** 没有完整官方训练集时，不把公开上游重建数据称为官方 v2 数据，也不把近似训练结果与官方 v2 混报。
8. **飞书同步前人工复核本草稿。** 确认标题、结论强度和 Next Actions 后，再单独执行同步；本次不自动推送。

