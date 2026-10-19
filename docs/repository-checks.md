# 主分支保护与自动检查

main 要求通过 PR 合并，并通过 GitHub Actions 的 `Documentation links` 与 `Large files` 两项检查。合并前分支需包含最新 main，评审讨论需解决；管理员同样适用，禁止 force push 和删除 main。

当前没有硬性要求其他成员批准（审批人数为 0），以适应目前只有一个管理员的状态；团队仍按 CONTRIBUTING 约定邀请同伴评审。新增协作者后可再设最低审批人数。管理员可以修改仓库规则，这些限制不是对管理员账户权限本身的撤销。

## 文档链接

使用 lychee 0.24.2 检查仓库中的 Markdown，包括 `.github/` 下的 Markdown：

- 相对/仓库根路径、图片目标、引用式链接、文件内及跨文件锚点。
- 忽略代码片段中的示例路径和 URL。
- 仅做离线检查；外部 HTTP/HTTPS 网站不发请求，也不作为阻断项，避免网站防爬或短暂故障阻塞提交。

已安装相同版本 lychee 时，在仓库根目录运行：

```bash
lychee --offline --include-fragments=anchor-only --hidden --no-progress --root-dir "$PWD" './**/*.md'
```

发现错误后修正相对路径、目标文件名或标题锚点，重新提交到原 PR。引用的文件需要一并提交；仅存在于个人电脑上的目标不能通过干净 CI 检查。

## 大文件

单个 Git blob 上限 **10 MiB（10,485,760 字节）**，等于上限允许，超过上限失败。检查 HEAD 的全部文件，并检查 PR 中新提交的历史对象。因此，加入大文件后再删除，也会被拦截。

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/check_large_files.py --base-ref origin/main
```

先 fetch 保持 origin/main 最新。脚本检查已提交的 Git 对象；未跟踪文件和未提交改动不在范围内。没有 `--base-ref` 时仅检查 HEAD，手动触发 workflow 也仅检查 HEAD；PR 与 main push 自动提供对应基准。

超大文件需要从本 PR 的所有新提交中移除，将原始数据/权重存到外部，再提交元数据。不要只追加删除提交。可以从最新 main 建一个干净分支，仅复制需要的文本/代码并提交，另开 PR 替代有问题的 PR；重写已共享分支历史前与协作者协调。

历史中已在基准前删除的大文件不会使每个新 PR 失败；仍存在于 HEAD 的超大文件始终失败。LFS 指针按指针本身的 Git 大小检查，不下载或审核其远端内容。检查也不是凭据或数据许可扫描。

## 配置与维护

实现位于 [workflow](../.github/workflows/repository-checks.yml)、[大小检查脚本](../scripts/check_large_files.py) 和 [测试](../tests/test_large_files.py)。必需检查没有路径过滤：文档、代码或日志 PR 都会运行。CI 只有 contents 读取权限，不保存 checkout 凭据，Action 固定到完整 commit。

[main-protection.json](../.github/main-protection.json) 保存保护配置，检查绑定到 GitHub Actions App（15368）。它是管理员显式应用的配置，不会因文件被编辑而自动更改线上规则。管理员需要更新配置时，在核对当前线上规则后执行：

```bash
gh api --method PUT repos/wxie9/dummy-test-001/branches/main/protection --input .github/main-protection.json
gh api repos/wxie9/dummy-test-001/branches/main/protection
```

更改 workflow 的 job 名称时，须同步更新线上必需检查，避免 PR 永久等待一个不存在的检查。首次安装先确认 PR 上两个 job 实际成功，再启用保护并正常合并。
