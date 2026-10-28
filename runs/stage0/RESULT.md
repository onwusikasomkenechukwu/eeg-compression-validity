# Stage 0 result (CHB-MIT, EpiDeNet, patient-specific, 3 seeds)

Run: 414/414 jobs, 0 failed; started 2026-10-25 13:48 UTC after the OSF registration, paused once (2026-10-26), finished 2026-10-26 22:57 UTC; code commit 3a9b77d (MANIFEST.md). Registered analysis: `summary.md` (analyze_frontier.py), `stats.md` (analyze_stats.py), `sanity_gate.md` (sanity_gate.py, written after the run to apply the registered gate rule as stated; it adds no new criterion).

## 1. FP32 sanity gate: FAIL (part B)

| Part | Result | Registered rule | Verdict |
|---|---|---|---|
| A. Seizures detected (EpiDeNet definition) | 92.6% (171, 172, 171 of 185 by seed) | >= 82.3% | pass (EpiDeNet: 91.2%) |
| B. Voted window false positives per hour | 5.83 (6.29, 5.23, 5.96) | 1.12-4.48 | **fail** (EpiDeNet: 2.24) |

Under the registration, a gate failure means the reimplementation is wrong, not the hypothesis; the results below are therefore not confirmatory as they stand.

Diagnosis (exploratory):
- Operating point, not detection ability: detection is higher than EpiDeNet's, while pooled test window specificity is 0.9904 (EpiDeNet 0.9952) against the 0.995 target set on validation. Thresholds set on one neighboring fold's seizure-free hours transfer to test with a downward bias (seen first on the chb01 pilot), roughly doubling raw false-positive windows (8.66/h vs EpiDeNet's 4.29).
- The 3-window vote removes 33% of false-positive windows here vs 48% in EpiDeNet.
- Concentration: chb09 (20.6/h) and chb07 (13.8/h); the top 5 patients carry 52% of voted false-positive windows; the median patient is 4.07/h (inside the range).
- Pooled specificity is outside 0.995 +/- 0.005 for 20 of 72 patient-seed combinations.

## 2. Primary endpoint and stop rule (as registered)

Excess latency at FP32's false-alarm rate (s); pooled = median over seeds per patient, then over patients; null = FP32 seed pairs (144 ordered pairs), 95% band -5.87 to 9.57 s.

| Model | Pooled | 95% patient bootstrap | Mixed model mean [95% CI] | Censored (of 72) | Band | 2 s floor |
|---|---|---|---|---|---|---|
| **INT8 (primary)** | **0.22** | [0.00, 0.67] | 0.32 [-0.42, 1.06] | 0 | inside | below |
| sim8 (cross-check) | 0.00 | | | 0 | inside | below |
| sim6 | 0.83 | [-0.46, 2.00] | 2.37 [0.73, 4.00] | 4 | inside | below |
| **sim4** | **20.71** | [6.42, unbounded] | 10.55 [6.85, 14.25] | **24** | **outside** | **above** |
| QAT 8-bit | 0.33 | [0.00, 1.00] | 0.90 [-0.13, 1.92] | 0 | inside | below |

Stop rule: **CONTINUE**, because 4-bit clears both the band and the floor (the registered branch: "where compression starts to cost latency"). INT8 shows no frontier shift. Censored = the model never came down to FP32's false-alarm rate at any smoothing width (a third of 4-bit's patient-seed values). The mixed model uses finite values only. Undefined (FP32 itself missed half or more of a patient's seizures): 3 patient-seed values per model.

## 3. Exploratory

- H2 (dose-response): monotone, INT8 0.2 s < 6-bit 0.8 s (mixed model 2.4 s) < 4-bit 20.7 s.
- H3 (dwell predicts each patient's shift): **not supported**; Spearman rho across patients -0.14 to 0.20 for all models and band widths.
- H3 premise: quantization error autocorrelation falls from 0.69 (1 s) to 0.16 (8 s) for INT8, but stays higher for 4-bit (0.82 to 0.36): 4-bit errors persist long enough to survive smoothing.
- Window-counted FP/h vs SzCORE false alarms (same FP32 model): median 9.5x across 24 patients.

## 4. Decision needed (review of design choices)

The gate failed on the false-positive side while detection exceeded EpiDeNet's. Before any rerun, the registration should be updated with whatever changes, and the failed gate reported in the paper either way.
