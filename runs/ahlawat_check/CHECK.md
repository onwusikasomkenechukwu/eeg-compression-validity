# Ahlawat (2026) code check

Ran `code/brain-inspired-computing/final.py` unchanged on CHB-MIT, on his own split. Full output: `run.log`; full table: `processed_chb_mit/quantization_results.csv`.

## Result: reproduces

| Model | Test AUC | Paper |
|---|---|---|
| FP32 | 0.9618 | 0.9617 |
| Dynamic INT8 (PyTorch) | 0.9620 | |
| Static eager INT8 | 0.9604 | |
| Static FX INT8 | 0.9618 | |
| QAT FX INT8 | 0.9633 | |
| Dynamic INT8 (ONNX) | 0.9618 | |
| Static QDQ INT8 (ONNX) | 0.9618 | |
| Fused FX INT8 | 0.9610 | |
| All INT8 variants | 0.9604 to 0.9633 | 0.9609 to 0.9628 |

Preprocessing gives 11,145 windows, the paper's count. Other stages: SNN conversion 0.9555; 8-channel retrains 0.9502 and 0.9634 (same code run twice, see below); 8-channel + 2:4 pruning 0.9577.

## Findings for the plan

- **The split leaks, confirmed in code** (`final.py` lines 1122-1144): windows from all patients are pooled and split at random, with 8 s windows every 4 s, so overlapping windows land on both sides. The split is 56/24/20 (20% test, then 30% of the rest for validation), not 60/20/20.
- **Seed noise dwarfs the reported INT8 effect.** The 8-channel retrain cell appears twice in `final.py` (lines 1484 and 1530); the two identical runs differ by 0.013 test AUC, against INT8 deltas of about 0.001-0.002.
- **Threshold-free metric only.** Every number is window-level AUC; no event-level false alarms or latency, which is the gap this paper targets.

## Environment deviations (needed to run, not changes to his code)

- `PYTHONIOENCODING=utf-8`: the Windows console's default encoding cannot print the `Δ` in his results tables (run 1 crashed there; `run1_crashed.log`).
- PyTorch 2.7.1 in `.venv-ahlawat/`, not his `>=2.9.1`: Windows builds of 2.9.1 and later ship no FBGEMM quantization engine, which his code hard-codes (run 2 stopped there; `run2_fbgemm_missing.log`). FP32 AUC is identical across 2.14 and 2.7.1.
- Runs on CPU. FP32 training stopped early at epoch 172, at about 30 s per epoch.
