# FP32 sanity gate (pre-registered)

| seed | jobs | seizures detected | detection rate | voted window FP/h | hours |
|---|---|---|---|---|---|
| 0 | 138 | 171/185 | 0.924 | 6.29 | 980 |
| 1 | 138 | 172/185 | 0.930 | 5.23 | 980 |
| 2 | 138 | 171/185 | 0.924 | 5.96 | 980 |

Mean over seeds: detection 0.926 (pass if >= 0.823): **PASS**; voted window FP/h 5.83 (pass if within (1.12, 4.48)): **FAIL**.

Gate: **FAIL**. EpiDeNet: 165/181 detected (0.912), 2.24 FP/h with its vote.
