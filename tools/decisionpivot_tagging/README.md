# DecisionPivot taxonomy tagging

Tags Kev v2 reconstruction rows with the DecisionPivot Core 1.1 hierarchy:

- layer A–G (or O for `other`);
- one of the 13 Core task families (or `other`);
- one controlled fine category;
- optional secondary family and confidence.

The classifier uses `qwen3.8-flash` with thinking disabled and JSON output. It is resumable and reads the API key only from `DASHSCOPE_API_KEY`.

Example:

```bash
python3 tag_v2.py \
  --input hard=/path/hard-v1-train.jsonl \
  --output-dir /path/output \
  --batch-size 8 --concurrency 8
```

The output is an alignment analysis, not an official Kev dataset reconstruction. Long states are truncated into head/tail task fingerprints for classification; the original training files are not modified.
