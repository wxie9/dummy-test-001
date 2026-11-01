# H20 4B / 9B weak-seven three-epoch comparison

Started 2026-10-31 at about 16:05 CST on the H20 host. These are fresh runs from the original stage checkpoints, not two extra epochs appended to the one-epoch candidate. The only planned training change from `launch_4b.sh` and `launch_9b.sh` is `--epochs 3` instead of `--epochs 1`; both use the same local targeted JSONL files, 6000 decision-v7 replay rows, seed 101, LR 1e-5, LoRA rank 16 plus pointer head, effective batch 8, and the same v6 augmentation settings.

Remote launcher: `/data/kev/local_data/h20_weak7_v6_20261031/run_3ep.sh` (local copy `run_3ep.sh`). Remote wrapper PIDs at launch: 4B 667548 on GPU 0, 9B 667549 on GPU 1. Input SHA256 checks matched `manifest.json` before launch. Both began loading/training successfully; no other GPU processes were present at the start.

Planned remote outputs:

- 4B checkpoint: `/data/kev/runs/h20-4b-weak7-v6-3ep-20261031/`
- 9B checkpoint: `/data/kev/runs/h20-9b-weak7-v6-3ep-20261031/`
- Development evaluations: corresponding checkpoint directory plus `-dev-after`
- Six frozen evaluations and completion marker: corresponding checkpoint directory plus `-eval`, with `ALL_DONE` in `status.log` only after every suite succeeds
- Training logs: `/data/kev/logs/h20-{4b,9b}-weak7-v6-3ep-20261031.log`

Results pending. Verify training metrics, suite hashes/denominators, rejected/truncated counts, and paired questions against the original and one-epoch checkpoint before drawing conclusions.

2026-10-31 later: multi-GPU LoRA support was deployed to `/data/kev/kev/train.py` after independent two- and four-GPU smoke tests. These active three-epoch runs remain their original single-GPU processes and were still alive immediately after deployment. See `multi_gpu_benchmark.md` for the measured 1/2/4-GPU comparison and production code hash.

2026-10-31 17:19 CST: At the user's request, the 9B single-GPU process group (wrapper PID 667549, trainer PID 667555) was stopped at its last logged `ep1 step 950/2814`. Its incomplete directory and logs were preserved; no intermediate LoRA checkpoint existed. The 4B single-GPU process (wrapper PID 667548) stayed active.

2026-10-31 17:20:57 CST: A fresh 9B three-epoch run started from `/data/kev/runs/h20-9b-s3/` on GPUs 2,3,4,5, wrapper PID 1844624, using `run_9b_3ep_4gpu.sh`. It uses the same SHA256-verified targeted input, 6000 replay records, seed 101, LR 1e-5, and effective batch 8 (`batch 2 × accum 1 × world 4`). Remote checkpoint `/data/kev/runs/h20-9b-weak7-v6-3ep-4gpu-20261031/`; development evaluation appends `-dev-after`; six-suite evaluation and completion marker append `-eval`. `device=cuda world=4` and all four GPUs allocated memory at startup. The existing heartbeat monitor was updated to watch this new 9B path and treat the old single-GPU stop as intentional.

2026-10-31 complete: 4B `ALL_DONE` at 18:18:40 CST; 9B four-GPU `ALL_DONE` at 19:58:47 CST. Both completed 2814 optimizer steps, development and six frozen suites without rejected/truncated records. Exact paired analysis, suite hashes and denominators: `three_epoch_results.md` and `three_epoch_comparison.json`. Six-suite correct counts original → one → three: 4B 4919→4921→4880/5999; 9B 5078→5073→5032/5999. Neither three-epoch checkpoint is promoted. Raw results are archived in `three_epoch_raw/`; the heartbeat was deleted after completion.
