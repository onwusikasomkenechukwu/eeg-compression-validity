# Reimplementation check rerun with unweighted cross-entropy (EpiDeNet's protocol; exploratory, post hoc)

| seed | jobs | seizures detected | detection rate | voted window FP/h | hours |
|---|---|---|---|---|---|
| 0 | 138 | 170/185 | 0.919 | 3.44 | 188 |
| 1 | 138 | 173/185 | 0.935 | 20.62 | 188 |
| 2 | 138 | 171/185 | 0.924 | 12.50 | 188 |

Mean over seeds: detection 0.926 (pass if >= 0.823): **PASS**; voted window FP/h 12.18 (pass if within (1.12, 4.48)): **FAIL**.

Gate: **FAIL**. EpiDeNet: 165/181 detected (0.912), 2.24 FP/h with its vote.

Descriptive (not a criterion): voted window sensitivity 70.59%, specificity 99.20%, mean over jobs (EpiDeNet: 68.73%, 99.75%).
