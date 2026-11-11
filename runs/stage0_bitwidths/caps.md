# Recall at a false-alarm cap (exploratory): runs/stage0_bitwidths

24 patient(s), 72 patient-seed values per model. SzCORE event sensitivity at the smoothing width with the most detected seizures among those with false alarms per 24 h at or below the cap.

## Cap: 0.5 false alarms per 24 h

| model | pooled sensitivity (median over seeds) | paired change vs FP32 (median of patients) | 95% patient-bootstrap CI | patients in paired change | cannot reach cap (of patient-seeds) |
|---|---|---|---|---|---|
| fp32 | 0.564 | n/a | n/a | n/a | 47/72 |
| int8 | 0.471 | 0.000 | [0.000, 0.000] | 11 | 45/72 |
| sim6 | 0.544 | 0.000 | [0.000, 0.000] | 11 | 40/72 |
| sim4 | 0.231 | -0.200 | [-0.250, 0.000] | 11 | 31/72 |
| w4a8 | 0.457 | 0.000 | [0.000, 0.000] | 11 | 43/72 |
| fp16 | 0.564 | 0.000 | [0.000, 0.000] | 12 | 47/72 |

## Cap: 1 false alarms per 24 h

| model | pooled sensitivity (median over seeds) | paired change vs FP32 (median of patients) | 95% patient-bootstrap CI | patients in paired change | cannot reach cap (of patient-seeds) |
|---|---|---|---|---|---|
| fp32 | 0.584 | n/a | n/a | n/a | 32/72 |
| int8 | 0.545 | 0.000 | [0.000, 0.000] | 18 | 27/72 |
| sim6 | 0.542 | 0.000 | [0.000, 0.000] | 16 | 25/72 |
| sim4 | 0.287 | -0.143 | [-0.200, 0.000] | 17 | 15/72 |
| w4a8 | 0.568 | 0.000 | [0.000, 0.000] | 17 | 29/72 |
| fp16 | 0.584 | 0.000 | [0.000, 0.000] | 18 | 32/72 |

## Cap: 2 false alarms per 24 h

| model | pooled sensitivity (median over seeds) | paired change vs FP32 (median of patients) | 95% patient-bootstrap CI | patients in paired change | cannot reach cap (of patient-seeds) |
|---|---|---|---|---|---|
| fp32 | 0.525 | n/a | n/a | n/a | 19/72 |
| int8 | 0.536 | 0.000 | [0.000, 0.000] | 21 | 18/72 |
| sim6 | 0.485 | 0.000 | [0.000, 0.000] | 21 | 12/72 |
| sim4 | 0.349 | -0.062 | [-0.250, 0.000] | 21 | 5/72 |
| w4a8 | 0.533 | 0.000 | [0.000, 0.000] | 20 | 19/72 |
| fp16 | 0.525 | 0.000 | [0.000, 0.000] | 21 | 19/72 |

