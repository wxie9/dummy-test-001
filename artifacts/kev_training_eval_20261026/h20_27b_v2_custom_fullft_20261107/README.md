# H20 Kev-27B custom v2-style full-parameter SFT start (2026-11-07)

This directory records the start evidence for a custom public/self-generated
Kev v2-style candidate. It is **not** the unreleased official 145,840-record
Kev v2 training corpus and must not be reported as an official reproduction.

## Data

- Candidate pool before exact-content deduplication: 115,047 records.
- Final training file: 114,627 records / 125,202 questions.
- Components after deduplication: 70,627 Kev corpus records, 24,000 selected
  Tasksource records, and 20,000 DecisionPivot-targeted records.
- Exact duplicate copies removed: 420, all encountered in the B1-v2 input.
- Training JSONL SHA-256:
  `7ed6345da12847d6f620b5dd077a8d50f0fad5cf77827c9dc8881358dc2cd980`.
- Full provenance and component hashes: `data_manifest.json`.

## Preflight and smoke

- Kev's own `load_records()` and `materialize()` accepted all 114,627 final
  records: 104,123 choice, 15,718 noul, and 5,361 score questions.
- Eight-H20 real-model FSDP2 smoke completed 2/2 optimizer steps with full
  weights, bf16, zero rejected/truncated records, finite gradient norms, and
  no OOM/NaN.
- Smoke generated 19,487 none-pair records and planned the full run as 896
  optimizer steps. The largest packed pass was 27,633 tokens under the 40,960
  limit.
- Smoke metrics/config are archived in this directory.

## Formal run

- Remote run: `/data/kev/runs/h20-27b-v2-custom114627-fullft8-20261107/`.
- Remote log: `/data/kev/logs/h20-27b-v2-custom114627-fullft8-20261107.log`.
- Initial torchrun PID: `960730`.
- Started: 2026-11-07 21:15 CST on GPU 0--7.
- Base: local `Qwen3.8-27B`, pinned revision
  `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`.
- One epoch, 896 planned optimizer steps, batch 8/GPU, accumulation 2,
  global requested batch 128, backbone LR 2e-6, head LR 1e-4, bf16,
  full-parameter FSDP2, max state 32,768, pass-token cap 40,960.
- Recovery snapshots requested at 25%, 50%, and 75%.

## Completion

- Completed at 2026-11-08 06:32:32 CST.
- Optimizer steps: 896/896; wall time: 33,107.03 seconds (9h 11m 47s).
- Requested records: 114,627; records seen after none-pair expansion: 153,601.
- Forward tokens: 71,304,292; rejected/truncated: 0/0.
- Gradient norm mean/max: 10.9775/217.5054; all 896 steps were clipped.
- Framework peak device memory: 83,468,725,760 bytes; peak rank-0 RSS:
  55,137,480,704 bytes.
- Final checkpoint: 48 GB, 11/11 indexed non-empty safetensor shards.
- Recovery snapshots exist at steps 224, 448, and 672 (144 GB total).
- Final key hashes:
  - `head.pt`: `83d1ed7eea9568e4ab0ce859a75bb48f8f23e36e1fc26e07bec3b735f7a2069a`
  - `training_config.json`: `bb4e76de6ce3b785e3fa0c83a89bd89458078d744eeefd29d8465a87eb5c9d97`
  - `training_metrics.json`: `c781277540580b24488ffaa13d1189e236f757793098b63ee62ee74cee17f431`
  - model index: `5af6c022747934e687d7edf362de832a7fa2c82eedc36a8679495b40bb214b6f`
- Final log scan found no traceback, OOM, CUDA error, NaN, or FAILED marker.

Completion evidence is archived as `final_train.log`,
`final_training_config.json`, `final_training_metrics.json`, and
`final_model_index.json`; `completion_evidence.tar.gz` has SHA-256
`e0da92447e95bf5524db7bacb567f18540919de7b87165d2b9e9310b684fcfd9`.

## Evaluation and 0.85/0.15 blend (2026-11-08)

The full-parameter checkpoint and an official-style custom blend were both
evaluated. The blend is **not** official Kev-27B v2: it uses this custom SFT
checkpoint and the locally trained v1 adapter.

- Blend formula: `0.85 * custom full SFT + 0.15 * local v1`, computed in
  fp32 and rounded once to the SFT dtype.
- The SFT pointer head was retained; the v1 head was not blended.
- Full-SFT weights SHA-256:
  `ea5e8e601700ced6ba138ead9ecf445901db38a1cadbf63e8c6ac30af17ecd52`.
- v1 adapter SHA-256:
  `2254c36f318d23e83eeb363101b00fa840fd58f7bee7894c962520e1373bddfa`.
- Blended weights SHA-256:
  `e1b28c1689dab8adff349c36497c08e330b5952d9dd95469198de6b55e2ba824`.

DecisionPivot Core 1.1 used all 13 families and all 7,800 items:

| checkpoint | item accuracy | pair accuracy | seven-layer score |
| --- | ---: | ---: | ---: |
| local v1 baseline | 68.83% | 41.67% | 43.92 |
| official v2 checkpoint baseline | 70.54% | 44.05% | 46.19 |
| custom full SFT | 70.72% (5,516/7,800) | 45.43% | 48.47 |
| custom 0.85/0.15 blend | **71.12% (5,547/7,800)** | **46.02%** | **49.03** |

The blend improved over the custom full SFT by 31 items, +0.59 percentage
points in pair accuracy, and +0.57 seven-layer points. All families had full
coverage. Because the 20,000-record targeted component was allocated using
DecisionPivot weakness categories, these scores are targeted-repair evidence,
not a blind generalization estimate.

As a regression check, the six frozen Kev suites scored 5,208/5,999 (86.81%)
for the full SFT and 5,206/5,999 (86.78%) for the blend, with zero rejected or
truncated records in both evaluations.

Machine-readable evidence is under `evaluation/`: both DecisionPivot
`scores.json` files and summaries, both six-suite summaries, the v1/v2
DecisionPivot baselines, and `interpolation-w85.json`.
