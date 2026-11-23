# Excess latency at FP32's false-alarm rate (s): runs/stage1_ahlawat_ws_bitwidths

24 patient(s). Pooled = median over seeds per patient, then over patients.

| model | pooled | 95% patient-bootstrap CI | mixed model mean [95% CI] | censored | undefined |
|---|---|---|---|---|---|
| int8 | -0.13 | [-0.30, 0.00] | 0.01 [-0.18, 0.21] | 0/120 | 9 |
| sim6 | 0.00 | [-0.27, 0.31] | 3.70 [-2.96, 10.35] | 3/120 | 9 |
| sim4 | 16.17 | [2.79, 32.75] | 10.34 [4.56, 16.11] | 31/120 | 9 |
| w4a8 | 0.00 | [-0.14, 0.00] | 0.17 [-0.04, 0.38] | 0/120 | 9 |
| fp16 | 0.00 | [0.00, 0.00] | -0.03 [-0.08, 0.02] | 0/120 | 9 |

