# 数据入口

Git 保存 [元数据表](../metadata/README.md)、数据说明和后续采用的数据版本指针。训练语料、tokenized 缓存和大型评测数据保存在外部存储。训练、验证和测试 split 明确区分，筛选与去重产生新版本并登记。

本地按需创建的 `raw/`、`interim/`、`processed/`、`external/`、`private/` 和 `local/` 已被 Git 忽略。小型可共享测试数据放在 `tests/fixtures/`，不放进忽略目录。

当前没有已配置的数据源、共享存储地址或下载命令。首次共享数据前按 [数据管理](../docs/data-management.md) 配置存储、访问方式与备份，并登记版本和校验和。
