# JEV 科研协作骨架 Implementation Plan

> 执行方式：在当前会话按清单顺序实施并检查；本次交付是文档、模板和 GitHub 表单，不新增分析软件。

**Goal:** 交付团队可以直接使用的文献、湿实验与计算研究协作骨架。

**Architecture:** 一个主仓库组织文本、代码和元数据，外部存储保管大型原始数据；模板与统一编号连接研究活动。

**Tech Stack:** Markdown、BibTeX、TSV、GitHub Issue Forms YAML、Git。

## 全局约束

- 中文说明优先，路径及 ID 使用 ASCII。
- 不假设科学问题、成员名单、编程语言和远程数据存储已确定。
- 不生成真实研究结论或示例实验结果。
- 不安装第三方 skills，不部署数据或流程服务，不修改远程协作设置。
- 每个实验或运行单独建目录；模板为唯一字段规范。

## Task 1：协作入口与规则

- [x] 更新 `README.md`，创建 `CONTRIBUTING.md`、`AGENTS.md`、`.gitignore` 和文本换行规则 `.gitattributes`。
- [x] 创建 `docs/conventions.md`、`docs/data-management.md` 和 `docs/references.md`。
- [x] 检查 README 新成员路径、编号规则及存储说明是否一致。

## Task 2：研究目录与模板

- [x] 为各研究目录创建 README；创建 `metadata/members.tsv`、`metadata/samples.tsv`、`metadata/datasets.tsv` 表头和空 BibTeX 文件。
- [x] 在 `templates/` 创建文献、检索、问题、假设、方案、湿实验、计算运行、决策、周报模板。
- [x] 检查模板覆盖来源、版本、原始观察、结论边界、失败记录和更正记录。

## Task 3：GitHub 协作表单

- [x] 创建文献、实验、分析三个 Issue Forms，包含负责人、交付物和关联字段。
- [x] 创建 PR 模板和禁用空白 Issue 的表单配置；不依赖尚未创建的远程 labels、Projects 或 CODEOWNERS 用户。
- [x] 用系统 Ruby Psych 解析 YAML，检查 required 字段、唯一 ID 和顶层结构，无需安装依赖。

## Task 4：验收与交付

- [x] 检查所有 Markdown 相对链接；检查 TSV 表头和模板必备字段。
- [x] 在临时目录从模板创建虚构文献、实验和运行记录，演练稳定 ID、执行时 commit 和失败结果。
- [x] 检查忽略规则能排除原始数据、凭据和运行产物，保留模板和小型测试数据。
- [ ] 运行 `git diff --check`，检查完整 diff，更新清单并创建本地提交。
- [ ] 推送协作分支并创建草稿 PR，向用户提供主入口、模板路径、验证结果与远程发布状态。
