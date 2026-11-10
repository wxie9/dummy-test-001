# Kev experiment archive through 2026-11-10

This is the public entry point for the Kev experiment evidence in
`wxie9/dummy-test-001`, branch `codex/kev-training-logs`.

## Scope

The archive covers the complete local experimental record available through
2026-11-10, with redundant and unsafe artifacts removed:

- early A800 Qwen3/Qwen3.5 reproduction logs;
- 0.8B targeted continuation and controls from v1 through v9, including data
  coverage, paired-view, learning-rate, multi-epoch, supervision and
  representation probes;
- H20 4B and 9B six-suite baselines, weak-seven continuation, multi-GPU runs,
  independent expansion and DecisionPivot before/after evaluation;
- Kev-27B v1 six-GPU LoRA training, six-suite evaluation and report;
- Kev-27B custom v2-style eight-GPU full-parameter training and evaluation;
- v2 public-data reconstruction, Tasksource selection, Pivot-targeted data
  generation, manifests and audits;
- DecisionPivot probability exports, Kev/StartLux comparisons, six-state
  learning analysis, the 1,709-item large-error audit and the detailed methods
  report;
- Evidence Log drafts, consolidated reports, figures, generation and analysis
  scripts, hashes, manifests, configs, metrics, logs and per-question results.

## Recommended reading order

1. `Kev_4B_9B_27B_v1_v2_评测指标总报告_20261104.md`
2. `续训版本总览_20261030.md`
3. `h20_weak7_v6_20261031/scaling_and_continuation_summary.md`
4. `h20_weak7_independent_expansion_20261031/expanded_results.md`
5. `h20_27b_v1_report_20261102/Kev-27B_v1训练与评测报告.md`
6. `h20_27b_v2_custom_fullft_20261107/`
7. `decisionpivot_probability_exports_20261110/large_error_analysis/Kev融合版_DecisionPivot概率错题与错因统计分析方法报告_20261110.md`
8. `Evidence_Log_20261110_Kev27B_DecisionPivot规则掌握与概率边际审计_draft.md`

## File-level verification

- `PUBLIC_ARCHIVE_MANIFEST_20261110.tsv` records the repository-relative path,
  byte size, SHA-256 and whether each file pre-existed or was newly archived.
- `PUBLIC_ARCHIVE_SUMMARY_20261110.json` records counts, bytes and exclusion
  reasons.

## Publication exclusions

The repository is public. The following are deliberately excluded:

- model weights and checkpoint tensors (`safetensors`, `pt`, `bin`, etc.);
- AccessKeys, API keys, SSH passwords, private keys and local environment files;
- caches, bytecode and `.DS_Store`;
- reproducible tokenizer copies and copied report-app runtime code;
- duplicate extracted evidence directories when the verified tarball is kept;
- `all_pairwise_question_gaps.csv`, a redundant derivative larger than
  GitHub's 100 MB single-file limit. Compact summaries, the 7,800-question
  exports and portable probability-analysis bundles remain in the archive.

These exclusions do not remove reported metrics, training/evaluation logs,
configs, manifests, hashes, reviewed datasets, or per-question result files.
