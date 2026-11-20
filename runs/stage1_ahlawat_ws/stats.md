# Statistics: runs/stage1_ahlawat_ws

24 patient(s); seeds per patient: [5]

## Excess latency at FP32's false-alarm rate (s)

| model | pooled (median of patient medians) | 95% patient-bootstrap CI | mixed model mean [95% CI] | patient SD | concentration (worst 20%) | censored |
|---|---|---|---|---|---|---|
| int8 | -0.13 | [-0.30, 0.00] | 0.01 [-0.18, 0.21] | 0.00 | 1.00 | 0 |
| sim6 | 0.00 | [-0.27, 0.31] | 3.70 [-2.96, 10.35] | 16.24 | 1.00 | 3 |
| sim4 | 16.17 | [2.79, 32.75] | 10.34 [4.56, 16.11] | 12.08 | 1.00 | 31 |
| qat8 | 0.00 | [-0.13, 0.00] | 0.22 [-0.74, 1.18] | 1.08 | 0.94 | 0 |

## H3: FP32 dwell near the threshold predicts each patient's shift

Dwell = share of FP32 test windows within 0.5 logits of the FP32 threshold (pre-registered width; others are sensitivity analyses). Spearman correlation across patients with the patient's median excess latency.

| model | rho, delta=0.25 | rho, delta=0.5 | rho, delta=1.0 |
|---|---|---|---|
| int8 | -0.12 | -0.13 | -0.09 |
| sim6 | 0.15 | 0.16 | 0.13 |
| sim4 | 0.02 | 0.01 | -0.02 |
| qat8 | -0.05 | -0.05 | -0.02 |

Per-patient dwell (delta = 0.5): chb01 0.0051, chb02 0.2064, chb03 0.0263, chb04 0.0024, chb05 0.0039, chb06 0.0312, chb07 0.0042, chb08 0.0035, chb09 0.1444, chb10 0.0062, chb11 0.2067, chb12 0.0070, chb13 0.0040, chb14 0.0079, chb15 0.0035, chb16 0.2882, chb17 0.0043, chb18 0.0076, chb19 0.0029, chb20 0.0018, chb21 0.0025, chb22 0.0696, chb23 0.0029, chb24 0.0276

## H3 premise: quantization error over time

Autocorrelation of (quantized - FP32) logit differences within test records, median over jobs:

| model | lag 1 s | lag 2 s | lag 4 s | lag 8 s |
|---|---|---|---|---|
| int8 | 0.71 | 0.63 | 0.48 | 0.27 |
| sim4 | 0.93 | 0.86 | 0.72 | 0.49 |

Overlapping windows share 3 of 4 s of input at lag 1 s, so some correlation at short lags is expected from the input alone; the question is how fast it decays relative to the smoothing width.

## Window-counted FP/h vs SzCORE false alarms (FP32, 12 s smoothing), per patient

chb01 1.7x, chb02 1.6x, chb03 3.9x, chb04 2.3x, chb05 1.8x, chb06 2.3x, chb07 1.7x, chb08 5.9x, chb09 4.5x, chb10 2.5x, chb11 1.8x, chb12 4.5x, chb13 6.1x, chb14 1.3x, chb15 4.6x, chb16 4.5x, chb17 1.3x, chb18 4.1x, chb19 2.9x, chb20 4.3x, chb21 1.6x, chb22 1.8x, chb23 3.8x, chb24 3.7x

Median ratio 2.7x over 24 patient(s) with at least one alarm.

