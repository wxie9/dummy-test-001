# Kev training and evaluation records — 2026-10-26

This archive contains the reproducibility records for two completed, independent
three-stage Kev decision-model runs on the A800 server:

- `runs/replica-20261026/`: Qwen3.5-0.8B Base reproduction.
- `runs/qwen3-06b-20261026/`: Qwen3-0.6B Base comparison run.

For each run it retains the pipeline status, provenance manifest, resolved stage
configs, LoRA adapter configuration, training metrics and logs, calibration
records, summary, and development/test benchmark reports. The two root pipeline
logs are also retained.

Deliberately excluded: model weights, tokenizer copies, and per-item prediction
rows. They are not needed to audit the run schedule and aggregate metrics, and
would make the Git history unnecessarily large.

The server source root was `/C20545/kev-08b-official-repro-20261026/`. Both runs
completed on 2026-10-27 China Standard Time. The Qwen3.5 run's `devtools-v1`
report counts 1,073 raw questions; the official Kev reporting convention excludes
two records sharing the reused `codereviewer/cls-test/19245` ID, leaving 1,071.
