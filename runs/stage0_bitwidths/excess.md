# Excess latency at FP32's false-alarm rate (s): runs/stage0_bitwidths

24 patient(s). Pooled = median over seeds per patient, then over patients.

| model | pooled | 95% patient-bootstrap CI | mixed model mean [95% CI] | censored | undefined |
|---|---|---|---|---|---|
| int8 | 0.22 | [0.00, 0.67] | 0.32 [-0.42, 1.06] | 0/72 | 3 |
| sim6 | 0.83 | [-0.46, 2.00] | 2.37 [0.73, 4.00] | 4/72 | 3 |
| sim4 | 20.71 | [6.42, n/a] | 10.55 [6.85, 14.25] | 24/72 | 3 |
| w4a8 | 0.50 | [0.00, 1.25] | 1.36 [0.66, 2.07] | 0/72 | 3 |
| fp16 | 0.00 | [0.00, 0.00] | -0.03 [-0.09, 0.03] | 0/72 | 3 |

