# LLM 元数据登记

TSV 使用 UTF-8、首行为列名，每行一条记录。单元格不含制表符或换行；多个值用分号连接。不适用写 `NA`，未知写 `pending:原因`，不填猜测值。日期用 `YYYY-MM-DD`。

| 表 | 唯一键 | 用途 |
| --- | --- | --- |
| [members.tsv](members.tsv) | member_id | 2–8 位大写字母/数字代号、GitHub 用户名、active/inactive；先注册合并再分配正式 ID |
| [datasets.tsv](datasets.tsv) | dataset_id + version + split | 固定训练/验证/评测数据，来源 revision、内容或清单定位、校验和、许可与访问方式 |
| [models.tsv](models.tsv) | model_id | 固定外部/基础模型与 tokenizer 的来源、revision 和许可 |
| [checkpoints.tsv](checkpoints.tsv) | checkpoint_id | 本项目训练 TR-ID、基础模型 M-ID、step、full/adapter/merged 类型、清单与恢复状态 |

数据集 `checksum_scope` 为 file/manifest；SHA-256 对应 content_uri 单文件或 manifest_uri 清单。目录内部各文件的 SHA-256 保存于清单内。

checkpoint 表的 manifest_sha256 校验 manifest_uri 清单本身；resume_state 为 full/partial/weights-only，实际恢复条件在来源训练日志中说明。共享模型和 tokenizer revision 尽量填完整来源 commit；若服务不提供不可变版本，记录可获得的版本信息和复现限制。

初始表格均只有表头，没有真实成员、数据、模型或 checkpoint。并发追加需保留双方记录并检查唯一键。模型权重、语料与凭据不进入这些表；见 [数据管理](../docs/data-management.md)。
