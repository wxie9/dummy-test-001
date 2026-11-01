# H20 Kev 4B / 9B weak-seven continuation, 2026-10-31

This experiment starts from the existing H20 Kev-4B stage 4 and Kev-9B stage 3 checkpoints. Each model has its own bottom seven categories, determined from the pre-training hard-v1 and devtools-v1 test predictions. The choice of categories has therefore already used these tests; any post-training gain on them is diagnostic, not a blind held-out result.

## Input construction

- Each targeted corpus contains 1,500 records. Training adds 6,000 decision-v7 train records sampled with `random.Random("replay:101")`, matching the v6 report's 1:4 targeted-to-replay ratio.
- V6 solver-labelled records are reused for tool routing, temporal/numeric, probability, prompt injection, long policy, and multi-hop. The existing tool, temporal and injection records are preserved as requested in the earlier v6 line of work; the report notes ambiguity in some refund date boundaries.
- CodeReviewer, CommitPackFT, and FlakeFlagger records come from devtools-v1 train. The builder excludes any train record with a duplicate train ID or an ID, full state, or supplied text hash present in development/test. It selects balanced labels with seed 101.
- A separate full-state and ID audit against every hard-v1 and devtools-v1 development/test record found zero exact overlaps for both 1,500-record targeted corpora. This does not rule out shared templates or semantic similarity.
- `manifest.json` records exact source and output hashes and per-family counts. `train_4b.jsonl` and `train_9b.jsonl` are the frozen targeted inputs. The scripts do not change any frozen Kev suite.

| Model | Seven target categories | Targeted records | Targeted subquestions |
|---|---|---:|---:|
| 4B | temporal/numeric, tool routing, code review, prompt injection, probability, code-change understanding, test flakiness | 1,500 | 2,170 |
| 9B | temporal/numeric, code review, tool routing, code-change understanding, long policy, probability, multi-hop | 1,500 | 2,510 |

## Training

Both run for one epoch with seed 101, LoRA rank 16 plus the existing pointer head, frozen backbone, AdamW, LR 1e-5, weight decay 0.01, BF16 compute, FP32 backbone weights, gradient checkpointing, global batch 8 (`batch 2 × accum 4`), max state 7552, and v6 augmentation probabilities. The launches use H20 GPU 0 and 1 respectively. `launch_4b.sh` and `launch_9b.sh` are exact commands.

## Evaluation

`development_4b.jsonl` and `development_9b.jsonl` combine v6 and devtools development records from the seven corresponding categories. They are disjoint from this experiment's targeted train records by full-state hash. They are scored through `devsuite_4b` and `devsuite_9b` manifests with a 7552-token state limit. An initial direct `--data` evaluation used the program's 384-token default and rejected long records; those partial outputs are superseded by the full-context development runs. Before and after predictions are paired by question ID, source, task, answer options, and label.

The six frozen suites are decision-v7, transfer-v4, transfer-v9, hard-v1, devtools-v1, and documents-v1. `evaluate_six.sh` runs all six after a checkpoint finishes. The two baseline checkpoints were trained on related source distributions, so development performance is not a guarantee of wholly new-source generalization.

`post_train.sh` waits for each checkpoint's completed `training_metrics.json`, then runs the full-context development panel and all six frozen test suites on that model's training GPU. Its completion marker is `ALL_DONE` in the corresponding post log. This avoids scoring a partially saved checkpoint.

## Completed run and interpretation

Both continuation runs and all evaluations completed on 2026-10-31. Each optimizer ran 938 updates with zero rejected or truncated training records. The 4B training wall time was 2,326.6 seconds (38.8 minutes); the 9B time was 4,339.8 seconds (72.3 minutes). The full paired category tables and six-suite comparisons are in `results.md`; machine-readable counts are in `analysis.json`.

| Model | Target seven categories | Other six categories | Development panel |
|---|---:|---:|---:|
| 4B | 837/1173 → 853/1173 (+1.36 pp) | 841/988 → 835/988 (-0.61 pp) | 568/813 → 579/813 (+1.35 pp) |
| 9B | 910/1198 → 919/1198 (+0.75 pp) | 870/963 → 864/963 (-0.62 pp) | 585/839 → 640/839 (+6.56 pp) |

All six post-training suite reports match the corresponding baseline suite hashes and denominators; post-training evaluation rejected/truncated zero records. Neither model improved consistently across the six suites. Category selection used hard-v1 and devtools-v1 test scores, so gains there are diagnostic rather than new blind validation. The development panel shares source families or generation templates with training; its larger 9B gain did not carry over proportionately to the frozen tests. Both checkpoints remain candidates rather than replacements for their preceding stage checkpoints.

Remote checkpoints: `/data/kev/runs/h20-4b-weak7-v6-20261031/` and `/data/kev/runs/h20-9b-weak7-v6-20261031/`. Their adapter and head hashes are in `checkpoint_hashes.json`. Local `4b_post_bundle.tar.gz` and `9b_post_bundle.tar.gz` preserve raw evaluation reports, paired rows, logs and training metadata. The base model weights stay on the H20 data disk.

## Three-epoch follow-up

At the user's request, each model was restarted from its original stage checkpoint for three epochs on the same targeted input and replay recipe. The 4B run stayed on one GPU; the initial 9B one-GPU three-epoch run was intentionally stopped without a checkpoint, then restarted from stage 3 on four GPUs. Both replacement runs and all evaluations completed on 2026-10-31. The final 4B and 9B checkpoints are `/data/kev/runs/h20-4b-weak7-v6-3ep-20261031/` and `/data/kev/runs/h20-9b-weak7-v6-3ep-4gpu-20261031/`.

`three_epoch_results.md` contains the category and six-suite tables for original → one epoch → three epochs. `three_epoch_comparison.json` contains the exact paired counts, coverage and hashes; `analyze_three_epoch.py` reproduces the audit. `three_epoch_raw/` archives the original, one-epoch, and three-epoch per-question results, training metrics/configs, logs, and new checkpoint hashes. The downloaded tarball hashes are in `three_epoch_archive_hashes.txt`.

The six-suite weighted total was 4B **4919 → 4921 → 4880/5999** and 9B **5078 → 5073 → 5032/5999**. Development panels rose while the frozen tests fell, so neither three-epoch checkpoint replaces its original checkpoint. The 9B one- versus three-epoch comparison also changes GPU count, although global batch remains eight.

`scaling_and_continuation_summary.md` reorganizes the 0.8B/4B/9B original-checkpoint scaling results and 4B/9B one-/three-epoch continuation results, including per-category accuracy changes for each model's seven trained target categories. `make_scaling_continuation_summary.py` regenerates it from the audited JSON and original 0.8B reports.
