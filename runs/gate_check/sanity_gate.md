# Protocol-matched reimplementation check (EpiDeNet's protocol, registered update)

| seed | jobs | seizures detected | detection rate | voted window FP/h | hours |
|---|---|---|---|---|---|
| 0 | 138 | 175/185 | 0.946 | 6.03 | 188 |
| 1 | 138 | 178/185 | 0.962 | 24.15 | 188 |
| 2 | 138 | 175/185 | 0.946 | 16.51 | 188 |

Mean over seeds: detection 0.951 (pass if >= 0.823): **PASS**; voted window FP/h 15.56 (pass if within (1.12, 4.48)): **FAIL**.

Gate: **FAIL**. EpiDeNet: 165/181 detected (0.912), 2.24 FP/h with its vote.
