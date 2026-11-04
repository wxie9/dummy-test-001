# H20 Kev experiment archive

This index covers the H20 Kev 4B/9B training and evaluation artifacts collected
between 2026-10-30 and 2026-11-01. Model weights, access credentials, SSH
passwords, caches, and unrelated workspace files are intentionally excluded.

## Contents

- `Kev_4B_9B_27B_v1_v2_评测指标总报告_20261104.md`: consolidated
  evaluation report covering the local 4B/9B checkpoints and continuation
  experiments, the local 27B v1 reproduction, and clearly labelled official
  27B v2 results.
- `h20_4b_s4_six_test_20261030.md`: original Kev 4B stage-4 six-suite result.
- `h20_9b_s3_six_test_20261030.md`: original Kev 9B stage-3 six-suite result.
- `h20_weak7_error_neighborhood_20261031/`: model-specific weak-category
  error-neighborhood datasets, manifests, and audit notes.
- `h20_weak7_v6_20261031/`: one-epoch and three-epoch weak-seven continuation
  logs, configs, raw paired rows, evaluation reports, distributed-training
  launchers, speed checks, and analyses.
- `h20_weak7_independent_expansion_20261031/`: independently generated weak
  category expansion data, quality audits, 4B two-GPU and 9B four-GPU training
  records, development results, six frozen-suite results, and tool-routing
  diagnosis.
- `h20_decisionpivot_20261101/`: DecisionPivot Core 1.1 before/after results for
  Kev 4B and 9B, including all four 7,800-item runs, official scores, dataset and
  checkpoint hashes, and the detailed comparison report.

## Interpretation constraints

- Weak categories were selected using `hard-v1` and `devtools-v1`; their category
  improvements are diagnostic rather than independent blind-test evidence.
- The expanded 4B checkpoint improves the weighted six-suite aggregate but
  damages a tool-call decision boundary. The expanded 9B checkpoint is broadly
  flat on the six frozen suites.
- DecisionPivot shows no reliable overall accuracy improvement after continuation.
- The 4B original and continued checkpoints use different probability
  temperatures, so calibration metrics such as ECE and Brier are not directly
  comparable; top-choice and contrast-pair accuracy remain comparable.
- Archives are retained alongside extracted files where they form part of the
  original evidence bundle. Checksums in the experiment folders identify the
  canonical contents.

Start with:

- `Kev_4B_9B_27B_v1_v2_评测指标总报告_20261104.md`
- `h20_weak7_v6_20261031/scaling_and_continuation_summary.md`
- `h20_weak7_independent_expansion_20261031/expanded_results.md`
- `h20_decisionpivot_20261101/summary.md`

