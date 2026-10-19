# Repository checks implementation plan

**Goal:** main 通过 PR 和必需检查合并，自动拒绝失效的仓库内文档链接与超过 10 MiB 的 Git 文件。

**Architecture:** 固定版本 lychee 验证链接；Python/Git 对象元数据验证文件；GitHub Actions 运行检查，GitHub branch protection 将检查设为必需。

## 执行清单

- [x] 在 `tests/test_large_files.py` 建立临时 Git 仓库测试：边界、工作区未跟踪文件、历史大文件、异常 base ref 和特殊文件名；先确认缺少检查实现会失败。
- [x] 实现 `scripts/check_large_files.py`，运行 `python3 -m unittest discover -s tests -p 'test_*.py' -v` 和当前仓库检查。
- [x] 固定 lychee 版本与 Action SHA，验证临时坏路径、坏锚点与合法链接。
- [x] 创建 `.github/workflows/repository-checks.yml`，两个 job 无路径过滤、只读权限、全历史 checkout；大文件 job 同时运行回归测试。
- [x] 更新 README、CONTRIBUTING、团队指南及 `docs/repository-checks.md`，提供本地命令、失败修复与检查范围。
- [ ] 独立评审并创建 PR，确认实际 Actions 成功；配置并读回 main 保护；正常合并并验证 main CI。
