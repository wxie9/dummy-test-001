# LLM 数据与模型产物管理

## 存储边界

| 内容 | 存储方式 |
| --- | --- |
| 文献笔记、代码、训练/评测配置、环境锁定文件、元数据 | Git |
| 小型、可共享的测试数据 | `tests/fixtures/`，说明来源与用途 |
| 精选指标摘要和图表 | `reports/`，关联 TR-ID/EV-ID |
| 训练语料、tokenized 缓存、大型评测数据 | 团队共享存储，Git 保存版本和清单 |
| 基础模型、checkpoint、适配器、优化器状态 | 模型存储，Git 保存 revision/清单与训练关联 |
| 完整预测、逐条分数、运行日志 | 团队共享存储，Git 保存定位和校验和 |
| 文献 PDF | Zotero 共享库或约定附件存储 |
| 令牌、密码与凭据 | 本地/运行平台的凭据配置，不进入 Git |

建议普通 Git 中单个文件控制在 10 MiB 内，这是项目起步约定。`.gitignore` 不会拦截已跟踪文件或强制添加，提交前仍需检查。

## 数据版本与 split

在 [datasets.tsv](../metadata/datasets.tsv) 按 `(dataset_id, version, split)` 登记。保存来源 URI、上游精确 revision、内容或清单 URI、SHA-256、许可/使用条件、负责人和访问方式。自定义 split 写清含义；公开数据同样固定 revision，不能只写名称。

原始数据保留不变；清洗、去重、tokenization、过滤、分割或样本顺序发生变化时保存相应配置和新版本。训练、验证与测试用途分开约定；在实验计划与评测协议中记录重叠/污染检查、调参边界和已知限制。

单文件可直接记录文件 SHA-256；目录保存包含相对路径和各文件 SHA-256 的清单，并记录清单本身的 SHA-256。校验和从真实文件计算：macOS 用 `shasum -a 256 文件路径`，Linux 用 `sha256sum 文件路径`。

## 模型与 checkpoint

[models.tsv](../metadata/models.tsv) 固定模型与 tokenizer 的来源和 revision，包括许可/使用条件。外部模型直接登记 M-ID，无需伪造本项目训练记录。

[checkpoints.tsv](../metadata/checkpoints.tsv) 登记本项目训练产生的固定 checkpoint：C-ID、来源 TR-ID、基础模型 M-ID、step、产物类型、内容/清单 URI、清单 SHA-256 和恢复状态。产物类型为 full/adapter/merged；适配器必须可找到基础模型与训练时 tokenizer 信息。

`resume_state` 记录 `full`、`partial` 或 `weights-only`，并在训练记录解释实际保存的优化器、调度器、RNG 与数据游标。只有权重的文件不能声称完整恢复了原训练状态。日志平台上的 run ID 在 TR/EV 记录中保存，不能替代代码/数据版本。

## 共享与备份

外部存储当前尚未配置。首次交接前，在本文补充真实地址、维护人、访问方式和备份/恢复安排。URI 应可长期定位，避免个人绝对路径、过期签名链接和带令牌的 URL；凭据另行注入。

共享产物不能只在成员个人电脑上。Git 备份不能恢复未进入 Git 的语料与 checkpoint；外部存储需要独立备份。若后续采用 DVC，仍需单独上传数据，`git push` 不会上传外部产物。

运行数量增多后可评估 MLflow 或团队已有的日志平台；实际平台与权限由任务确定，当前没有默认运行服务。
