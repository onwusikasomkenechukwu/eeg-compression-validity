# Excess latency at FP32's false-alarm rate (s): runs/stage2_siena_bitwidths

8 patient(s). Pooled = median over seeds per patient, then over patients.

| model | pooled | 95% patient-bootstrap CI | mixed model mean [95% CI] | censored | undefined |
|---|---|---|---|---|---|
| int8 | 5.50 | [0.92, n/a] | -1.33 [-9.28, 6.61] | 9/40 | 11 |
| sim6 | 11.50 | [0.57, n/a] | 3.70 [-2.22, 9.61] | 9/40 | 11 |
| sim4 | inf | [n/a, n/a] | n/a | 25/40 | 11 |
| w4a8 | 0.55 | [-0.50, 1.67] | 0.86 [-2.24, 3.95] | 3/40 | 11 |
| fp16 | 0.00 | [-1.00, 0.00] | -0.44 [-0.99, 0.11] | 0/40 | 11 |

