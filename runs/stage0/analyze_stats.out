# Statistics: runs/stage0

24 patient(s); seeds per patient: [3]

## Excess latency at FP32's false-alarm rate (s)

| model | pooled (median of patient medians) | 95% patient-bootstrap CI | mixed model mean [95% CI] | patient SD | concentration (worst 20%) | censored |
|---|---|---|---|---|---|---|
| int8 | 0.22 | [0.00, 0.67] | 0.32 [-0.42, 1.06] | 0.97 | 0.81 | 0 |
| sim6 | 0.83 | [-0.46, 2.00] | 2.37 [0.73, 4.00] | 3.03 | 1.00 | 4 |
| sim4 | 20.71 | [6.42, n/a] | 10.55 [6.85, 14.25] | 5.42 | 1.00 | 24 |
| qat8 | 0.33 | [-0.00, 1.00] | 0.90 [-0.13, 1.92] | 2.15 | 0.73 | 0 |

## H3: FP32 dwell near the threshold predicts each patient's shift

Dwell = share of FP32 test windows within 0.5 logits of the FP32 threshold (pre-registered width; others are sensitivity analyses). Spearman correlation across patients with the patient's median excess latency.

| model | rho, delta=0.25 | rho, delta=0.5 | rho, delta=1.0 |
|---|---|---|---|
| int8 | 0.08 | 0.14 | 0.19 |
| sim6 | -0.09 | -0.06 | 0.18 |
| sim4 | -0.09 | -0.14 | -0.05 |
| qat8 | 0.05 | 0.10 | 0.20 |

Per-patient dwell (delta = 0.5): chb01 0.0054, chb02 0.0393, chb03 0.0067, chb04 0.0052, chb05 0.0079, chb06 0.0194, chb07 0.0102, chb08 0.0036, chb09 0.0134, chb10 0.0136, chb11 0.0049, chb12 0.0088, chb13 0.0045, chb14 0.0072, chb15 0.0049, chb16 0.0221, chb17 0.0049, chb18 0.0058, chb19 0.0064, chb20 0.0067, chb21 0.0123, chb22 0.0123, chb23 0.0024, chb24 0.0074

## H3 premise: quantization error over time

Autocorrelation of (quantized - FP32) logit differences within test records, median over jobs:

| model | lag 1 s | lag 2 s | lag 4 s | lag 8 s |
|---|---|---|---|---|
| int8 | 0.69 | 0.47 | 0.18 | 0.16 |
| sim4 | 0.82 | 0.67 | 0.41 | 0.36 |

Overlapping windows share 3 of 4 s of input at lag 1 s, so some correlation at short lags is expected from the input alone; the question is how fast it decays relative to the smoothing width.

## Window-counted FP/h vs SzCORE false alarms (FP32, 12 s smoothing), per patient

chb01 6.0x, chb02 10.6x, chb03 10.8x, chb04 13.8x, chb05 6.8x, chb06 9.6x, chb07 29.0x, chb08 15.7x, chb09 29.1x, chb10 8.1x, chb11 5.4x, chb12 15.0x, chb13 7.6x, chb14 8.9x, chb15 13.9x, chb16 9.4x, chb17 6.3x, chb18 18.4x, chb19 11.2x, chb20 8.5x, chb21 8.4x, chb22 5.3x, chb23 15.1x, chb24 6.8x

Median ratio 9.5x over 24 patient(s) with at least one alarm.

