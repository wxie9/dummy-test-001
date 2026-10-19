# 团队成员使用指南

一次任务的基本流程是：**认领 Issue → 建分支 → 提交文件 → 发 PR → 请同伴评审 → 合并 main**。文献、代码和日志都按这个流程协作。

## 第一次参与

先确认有仓库写入权限，并已配置 GitHub 的 Git 认证。在自己的电脑上克隆：

```bash
git clone https://github.com/wxie9/dummy-test-001.git JEV
cd JEV
```

在 [成员表](../metadata/members.tsv) 注册一个唯一成员代号（2–8 位大写字母或数字），通过 PR 合并后再使用。然后在 GitHub 的 **Issues → New issue** 选择文献、训练或评测，填写负责人、目标和交付物。

以下文件名中的 `AA`、`YYYYMMDD`、`001` 和 `Author2026Topic` 都是示例，请替换为自己的代号、创建日期、未占用序号或文献引用键。完整规则见 [编号规范](conventions.md)。

每项任务开始编辑前，先执行本文“怎样提交到团队仓库”中的同步 main、建立分支步骤，再复制对应模板。

## 提交文献调研

每篇论文一份笔记，不把所有论文写进同一个文件：

```bash
mkdir -p literature/notes
cp templates/literature-note.md literature/notes/Author2026Topic.md
```

填写标题、作者、原文链接/DOI、方法、关键证据及页码/图表位置、局限和对项目的启发。只读了摘要就明确写“仅阅读摘要”。PDF 放共享文献库，笔记里保留定位。

如果是系统检索一个主题，再复制 [检索模板](../templates/literature-search.md) 到 `literature/searches/<L-ID>.md`，记录平台、完整检索式、日期和筛选结果。跨论文总结放 `literature/syntheses/`，链接每篇笔记；子目录按需创建。参考文献导入 [references.bib](../literature/references.bib) 由任务指定的维护者处理。

## 提交训练代码

| 内容 | 放在哪里 |
| --- | --- |
| Python 数据处理、训练与评测实现 | `src/` |
| 启动脚本、分布式启动入口 | `scripts/` |
| 训练/评测配置 | `configs/training/`、`configs/evaluation/` |
| 相关测试和小型测试数据 | `tests/` |

子目录按需创建。一个 PR 尽量完成一项改动，说明解决什么问题、实际启动命令、依赖/环境文件和验证结果。当前尚无统一训练框架或默认启动命令，新增入口时一起写明用法。

**训练前先提交代码、配置和环境文件**，再记录：

```bash
git rev-parse HEAD
git status --short
```

把得到的完整 commit hash 和工作区状态填入训练日志。若仍有未提交改动，按模板保存含未跟踪文件的完整快照。之后提交日志产生的新 commit 不替代执行时的代码版本。代码可先用 Draft PR 交付，运行后在同一分支追加日志。

## 提交实验日志

每次训练复制一份 [训练模板](../templates/training-run.md)：

```bash
mkdir -p experiments/training/TR-YYYYMMDD-AA-001
cp templates/training-run.md experiments/training/TR-YYYYMMDD-AA-001/record.md
```

运行前填写目的、关联实验计划、执行时代码、数据版本与 split、模型/tokenizer revision、配置、seed 和 GPU 环境。运行后补上实际命令、日志位置、退出情况、观察结果和 checkpoint；新产物登记到 [checkpoint 表](../metadata/checkpoints.tsv)，新数据/基础模型登记到 [元数据表](../metadata/README.md)。恢复训练时写清源 checkpoint、step 和实际恢复状态。

每次评测复制 [评测模板](../templates/evaluation-run.md) 到 `experiments/evaluation/<EV-ID>/record.md`。填写输入 checkpoint/模型、数据 split、[评测协议](../benchmarks/README.md) 版本、prompt、解码与计分设置、有效/失败条目数和实际指标。要比较多次运行时，可先复制 [实验计划模板](../templates/experiment-plan.md) 到 `experiments/plans/<E-ID>.md`，统一约定基线、变量和判断标准。

失败、中断和没有提升的运行也要记录；重跑使用新 TR-ID/EV-ID 并关联前次。未执行写“未执行”，未知写“待确认：原因”，不适用写明原因。不要把运行结束或 loss 下降直接写成模型能力提升。

## 怎样提交到团队仓库

开始新任务前，先保存现有工作；在干净工作区执行以下命令。分支名是示例，文献用 `lit/`，训练代码用 `train/`，评测用 `eval/`，日志整理可用 `exp/`。

```bash
git switch main
git pull --ff-only origin main
git switch -c lit/AA-topic-review
```

完成编辑后，检查并只添加本任务文件。下面以提交一篇文献笔记为例；代码或日志替换成对应的实际路径：

```bash
git status --short
git diff
git add literature/notes/Author2026Topic.md
git diff --cached
git diff --cached --check
git commit -m "docs: add topic literature note"
git push -u origin HEAD
```

打开 GitHub 上这个分支的 **Compare & pull request**，目标选 `main`。按 [PR 模板](../.github/pull_request_template.md) 写清改动、文件路径、关联 Issue、实际检查和待确认项，请一位同伴评审。任务完成用 `Closes #编号`，仍在继续用 `Refs #编号`。收到意见后在同一分支修改、提交、push，PR 会随之更新。

等待 `Documentation links` 和 `Large files` 两项检查通过后再合并；分支落后 main 时先同步最新改动，重新等待检查。main 已要求 PR 合并，不能直接 push。链接或大文件检查失败时，按 [自动检查说明](repository-checks.md) 修复。

只改文字也可在 GitHub 网页编辑/新增文件，选择**新建分支并创建 PR**；参考资料和笔记不要只留在 Issue 评论中。

## 提交前记住三件事

1. **大文件放外部：** 训练语料、权重、完整预测和大量原始日志放团队共享存储；Git 保存摘要、URI、精确版本和校验和。共享存储尚未配置时，先约定位置与访问方式。令牌和密码不提交。
2. **记录能追溯：** 文献能找到原文，训练能找到代码/数据/配置，评测能找到模型/checkpoint 与协议。更正追加原因，历史版本保留。
3. **如实报告验证：** 代码写明实际测试或冒烟验证；未运行就说明原因。纯文档检查链接和 `git diff --cached --check` 即可。

更多约定见 [协作流程](../CONTRIBUTING.md)、[模板索引](../templates/README.md) 和 [数据管理](data-management.md)。
