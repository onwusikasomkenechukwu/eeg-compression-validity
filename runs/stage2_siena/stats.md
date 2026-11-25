# Statistics: runs/stage2_siena

8 patient(s); seeds per patient: [5]

## Excess latency at FP32's false-alarm rate (s)

| model | pooled (median of patient medians) | 95% patient-bootstrap CI | mixed model mean [95% CI] | patient SD | concentration (worst 20%) | censored |
|---|---|---|---|---|---|---|
| int8 | 5.50 | [0.92, n/a] | -1.33 [-9.28, 6.61] | 7.46 | 1.00 | 9 |
| sim6 | 11.50 | [0.57, n/a] | 3.70 [-2.22, 9.61] | 2.27 | 1.00 | 9 |
| sim4 | inf | [n/a, n/a] | n/a (fewer than 3 patients) | n/a | 1.00 | 25 |
| qat8 | 0.58 | [-1.00, 5.50] | -1.08 [-5.69, 3.52] | 3.18 | 1.00 | 4 |

## H3: FP32 dwell near the threshold predicts each patient's shift

Dwell = share of FP32 test windows within 0.5 logits of the FP32 threshold (pre-registered width; others are sensitivity analyses). Spearman correlation across patients with the patient's median excess latency.

| model | rho, delta=0.25 | rho, delta=0.5 | rho, delta=1.0 |
|---|---|---|---|
| int8 | -0.60 | -0.60 | -0.60 |
| sim6 | -0.40 | -0.40 | -0.40 |
| sim4 | n/a | n/a | n/a |
| qat8 | 0.07 | 0.07 | 0.07 |

Per-patient dwell (delta = 0.5): PN00 0.0056, PN05 0.5193, PN06 0.0099, PN09 0.0918, PN10 0.2285, PN12 0.6320, PN13 0.7202, PN14 0.2007

## H3 premise: quantization error over time

Autocorrelation of (quantized - FP32) logit differences within test records, median over jobs:

| model | lag 1 s | lag 2 s | lag 4 s | lag 8 s |
|---|---|---|---|---|
| int8 | 0.90 | 0.81 | 0.63 | 0.36 |
| sim4 | 0.95 | 0.89 | 0.75 | 0.49 |

Overlapping windows share 3 of 4 s of input at lag 1 s, so some correlation at short lags is expected from the input alone; the question is how fast it decays relative to the smoothing width.

## Window-counted FP/h vs SzCORE false alarms (FP32, 12 s smoothing), per patient

PN00 12.8x, PN05 8.7x, PN06 2.6x, PN09 11.6x, PN10 6.2x, PN12 5.2x, PN13 18.8x, PN14 0.9x

Median ratio 7.5x over 8 patient(s) with at least one alarm.

