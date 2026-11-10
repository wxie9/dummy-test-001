# H20 Kev-27B v1 six-suite evaluation

- 27B v1 clean weighted: **4939/5999 = 82.33%**.
- Coverage: 5,378 records / 6,565 questions; rejected/truncated = 0/0.
- Evaluation-only local-base shim changed only the base path in a copied `head.pt`/adapter config; the original checkpoint stayed unchanged and the adapter SHA remained identical.

| Suite | 4B stage4 | 9B stage3 | 27B v1 | 27B−9B |
|---|---:|---:|---:|---:|
| decision-v7 | 86.92% | 86.67% | **87.25%** (1047/1200) | +0.58 pp |
| transfer-v4 | 83.99% | 86.74% | **88.72%** (582/656) | +1.98 pp |
| transfer-v9 | 77.53% | 80.50% | **84.51%** (884/1046) | +4.02 pp |
| hard-v1 | 80.06% | 83.55% | **77.94%** (848/1088) | -5.61 pp |
| devtools-v1 | 75.21% | 81.17% | **70.64%** (758/1073) | -10.53 pp |
| documents-v1 | 89.32% | 90.49% | **87.61%** (820/936) | -2.88 pp |
| **clean weighted** | **82.00%** | **84.65%** | **82.33%** (4939/5999) | **-2.32 pp** |

- Devtools official duplicate-ID exclusion: 756/1071 = 70.59%; adjusted six-suite weighted = 4937/5997 = 82.32%.
- This is not a pure scaling comparison: 27B v1 trained only on B1-v2, whereas the 4B/9B checkpoints used later multi-stage data including documents/devtools/skills. The pattern—better transfer, weaker hard/devtools/documents—matches that training-data difference.
