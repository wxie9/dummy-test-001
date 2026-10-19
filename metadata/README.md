# 元数据登记

TSV 使用 UTF-8、首行为列名，每行一条记录。单元格不含制表符或换行；多个 ID 用分号连接。不适用写 `NA`，尚未知写 `pending:原因`，不填猜测值。

| 表 | 唯一键 | 字段说明 |
| --- | --- | --- |
| [members.tsv](members.tsv) | `member_id` | 2–8 位大写字母/数字代号、仓库用户名、状态（active/inactive）；先注册合并，再用于正式 ID |
| [samples.tsv](samples.tsv) | `sample_id` | 来源实验 ID、父样本 ID、实际采集日期、负责人、仓库记录路径和必要备注 |
| [datasets.tsv](datasets.tsv) | `dataset_id` + `version` | 来源实验或公开 accession/DOI、样本 ID、文件/清单 URI 与 SHA-256、登记日期、负责人和访问说明 |

日期用 `YYYY-MM-DD`。样本表 `record_path` 为仓库相对路径；数据表 `source_record_or_accession` 填来源 E-ID、R-ID 或公开来源。公开数据下载日期记录在数据集备注中。

数据表 `checksum_scope` 填 `file` 或 `manifest`；`checksum_sha256` 对应 `content_uri` 的单文件或 `manifest_uri` 的清单文件。目录内部每个文件的校验和保存在清单内。

表格初始只有表头，没有真实成员、样本或数据。公共表的并发追加需检查 ID 冲突并保留双方记录。身份映射不进入这些表；存储规则见 [数据管理](../docs/data-management.md)。
