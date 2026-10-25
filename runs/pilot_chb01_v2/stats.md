# Statistics: runs/pilot_chb01_v2

1 patient(s); seeds per patient: [3]

## Excess latency at FP32's false-alarm rate (s)

| model | pooled (median of patient medians) | 95% patient-bootstrap CI | mixed model mean [95% CI] | patient SD | concentration (worst 20%) | censored |
|---|---|---|---|---|---|---|
| int8 | -0.13 | [n/a, n/a] | n/a (fewer than 3 patients) | n/a | n/a | 0 |
| sim6 | -0.55 | [n/a, n/a] | n/a (fewer than 3 patients) | n/a | n/a | 0 |
| sim4 | 0.81 | [n/a, n/a] | n/a (fewer than 3 patients) | n/a | 1.00 | 0 |

## H3: FP32 dwell near the threshold predicts each patient's shift

Dwell = share of FP32 test windows within 0.5 logits of the FP32 threshold (pre-registered width; others are sensitivity analyses). Spearman correlation across patients with the patient's median excess latency.

| model | rho, delta=0.25 | rho, delta=0.5 | rho, delta=1.0 |
|---|---|---|---|
| int8 | n/a | n/a | n/a |
| sim6 | n/a | n/a | n/a |
| sim4 | n/a | n/a | n/a |

Per-patient dwell (delta = 0.5): chb01 0.0054

## H3 premise: quantization error over time

Autocorrelation of (quantized - FP32) logit differences within test records, median over jobs:

| model | lag 1 s | lag 2 s | lag 4 s | lag 8 s |
|---|---|---|---|---|
| int8 | 0.66 | 0.41 | 0.15 | 0.11 |
| sim4 | 0.75 | 0.55 | 0.27 | 0.25 |

Overlapping windows share 3 of 4 s of input at lag 1 s, so some correlation at short lags is expected from the input alone; the question is how fast it decays relative to the smoothing width.

## Window-counted FP/h vs SzCORE false alarms (FP32, 12 s smoothing), per patient

chb01 6.0x

Median ratio 6.0x over 1 patient(s) with at least one alarm.

