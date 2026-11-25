# Statistics: runs/stage2_siena_cross

14 patient(s); seeds per patient: [5]

## Excess latency at FP32's false-alarm rate (s)

| model | pooled (median of patient medians) | 95% patient-bootstrap CI | mixed model mean [95% CI] | patient SD | concentration (worst 20%) | censored |
|---|---|---|---|---|---|---|
| int8 | inf | [17.50, n/a] | 8.60 [2.75, 14.46] | 0.42 | 1.00 | 28 |
| sim6 | inf | [4.44, n/a] | 17.41 [-15.62, 50.44] | 34.92 | 1.00 | 32 |
| sim4 | inf | [17.32, n/a] | 2.41 [-25.83, 30.64] | 21.47 | 1.00 | 34 |
| qat8 | 3.00 | [0.00, n/a] | 3.25 [-4.59, 11.08] | 10.73 | 1.00 | 11 |

## H3: FP32 dwell near the threshold predicts each patient's shift

Dwell = share of FP32 test windows within 0.5 logits of the FP32 threshold (pre-registered width; others are sensitivity analyses). Spearman correlation across patients with the patient's median excess latency.

| model | rho, delta=0.25 | rho, delta=0.5 | rho, delta=1.0 |
|---|---|---|---|
| int8 | -0.80 | -0.80 | -0.80 |
| sim6 | -1.00 | -1.00 | -1.00 |
| sim4 | -1.00 | -1.00 | -1.00 |
| qat8 | 0.15 | 0.15 | 0.15 |

Per-patient dwell (delta = 0.5): PN00 0.0088, PN01 0.0015, PN03 0.0100, PN05 0.0035, PN06 0.0000, PN07 0.0174, PN09 0.0002, PN10 0.0040, PN11 0.0306, PN12 0.1862, PN13 0.0060, PN14 0.0079, PN16 0.0055, PN17 0.0048

## H3 premise: quantization error over time

Autocorrelation of (quantized - FP32) logit differences within test records, median over jobs:

| model | lag 1 s | lag 2 s | lag 4 s | lag 8 s |
|---|---|---|---|---|
| int8 | 0.97 | 0.94 | 0.85 | 0.69 |
| sim4 | 0.97 | 0.94 | 0.85 | 0.67 |

Overlapping windows share 3 of 4 s of input at lag 1 s, so some correlation at short lags is expected from the input alone; the question is how fast it decays relative to the smoothing width.

## Window-counted FP/h vs SzCORE false alarms (FP32, 12 s smoothing), per patient

PN00 7.4x, PN01 6.0x, PN03 7.7x, PN05 2.9x, PN06 infx, PN07 26.0x, PN09 infx, PN10 2.0x, PN11 5.8x, PN12 8.6x, PN13 26.6x, PN14 1.8x, PN16 1.5x, PN17 5.4x

Median ratio 5.9x over 12 patient(s) with at least one alarm.

