# Pipeline gate (due Nov 15): chb01, 7 folds x 3 seeds

**Verdict: PASS.** All 21 jobs ran end to end (load, train FP32, post-training quantize to INT8 / sim8 / sim6 / sim4, threshold, smooth, score with SzCORE, latency) with no failures, in 40.7 min on WSL2 (2 workers x 4 threads). Full numbers: `summary.md`; frontier: `chb01_frontier.png`; per-job outputs in `chb01/`.

## Checks

| Check | Result |
|---|---|
| Jobs completed | 21/21 |
| Early stopping fired (not the 300-epoch cap) | 21/21 |
| ONNX FP32 export vs PyTorch, max abs logit difference | 4.8e-6 |
| Unit tests (`tests/test_core.py`) | 14/14 pass |
| FP32 test specificity within 0.995 +/- 0.005, pooled over the patient's held-out hours (the rule now) | **3/3 seeds** (0.9932, 0.9933, 0.9934) |
| Diagnostic: single ~6 h folds inside the band | 14/21 (all 7 misses below: 0.982-0.989; fold 2 misses on all 3 seeds) |

## FP32 against EpiDeNet's own reporting (4 s windows)

| | FP/h raw | FP/h with 3-window vote | seizures detected |
|---|---|---|---|
| chb01, seeds 0 / 1 / 2 | 5.89 / 5.84 / 5.47 | 2.22 / 2.52 / 2.22 | 7/7, 7/7, 6/7 |
| EpiDeNet, all CHB-MIT | 4.29 | 2.24 | 165/181 |

One patient only, so this is not the sanity gate, but the voted rate lands on EpiDeNet's.

## Same model, two meanings of "FP/h"

Window-counted FP/h (vote) is **5.7 to 6.4 times** SzCORE false alarms per hour (2.22-2.52 vs 0.35-0.44) for the same FP32 model and threshold.

## Excess latency to match FP32's false alarms (s)

| seed | int8 | sim8 | sim6 | sim4 | FP32 seed-pair null |
|---|---|---|---|---|---|
| definition in use: least smoothing >= 12 s | 0, 2, 0 | 0, 2, 0 | 0, 0, 0 | **4, 3, 3** | 0 to 2 |
| matched along the whole frontier (interpolated) | -0.1, 0.2, -0.1 | 0.0, 0.2, 0.0 | -0.5, -1.0, -0.5 | **1.9, 0.8, -0.1** | -0.6 to 0.9 |

The definitions disagree for sim4. At 12 s smoothing sim4 already raises fewer false alarms than FP32 but alarms later: it sits further down the same curve rather than on a shifted one (see the plot). The upward-only search scores that move as 3-4 s of "excess"; matching along the frontier does not. The upward search also moves in grid steps (12 -> 16 s smoothing adds about 2-4 s), which is where the 0 / 2 s values come from.

On this one patient INT8 sits inside the FP32 seed noise under either definition. Only sim4 shows a possible shift, and only under the upward-only definition.

## Decisions taken after the gate

1. **Primary endpoint: interpolated along the frontier** (adopted). Excess latency is the latency each model needs at exactly FP32's false-alarm rate, read off its whole frontier by linear interpolation (`src/frontier.py`). Re-analysis of the same 21 jobs (`summary.md`):

   | seed | int8 | sim8 | sim6 | sim4 |
   |---|---|---|---|---|
   | excess latency (s), seeds 0 / 1 / 2 | -0.1 / 0.2 / -0.1 | 0.0 / 0.2 / 0.0 | -0.5 / -1.0 / -0.5 | 1.9 / 0.8 / -0.1 |
   | extra false alarms per 24 h at FP32's latency | -0.6 / 0.6 / -0.6 | 0.0 / 0.6 / 0.0 | -1.8 / -3.0 / -1.8 | 38.5 / 10.4 / -1.2 |

   FP32 seed-pair null: -0.6 to 0.9 s (6 ordered pairs). The second row is large for sim4 on two seeds because FP32's 8 s latency sits on the steep part of the curve, where a fraction of a second swings false alarms a lot: the two forms of H1 are not equally stable, and the latency form is the primary one.
2. **Specificity band: pooled per patient and seed** (adopted), matching how false alarms are pooled over all held-out hours. The per-fold value stays as a diagnostic. Note that pooled specificity (0.993) sits below the 0.995 target on every seed: thresholds set on one neighboring fold's seizure-free hours transfer with a small downward bias.
3. **Quantization-aware training** is not built yet; the plan needs it for Stage 0 (compared against the seed band only).

## Timing

21 jobs (each: FP32 training + 4 quantized models + 9 frontier sweeps) in 40.7 min with 2 parallel workers: about 1.9 min of wall time per job. Stage 0 has 138 folds (not the plan's 129: CHB-MIT has 141 seizure records, 138 usable), so 414 FP32 jobs at 3 seeds: about 13 h, plus QAT once built.
