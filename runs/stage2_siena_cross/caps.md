# Recall at a false-alarm cap (exploratory): runs/stage2_siena_cross

14 patient(s), 70 patient-seed values per model. SzCORE event sensitivity at the smoothing width with the most detected seizures among those with false alarms per 24 h at or below the cap.

## Cap: 0.5 false alarms per 24 h

| model | pooled sensitivity (median over seeds) | paired change vs FP32 (median of patients) | 95% patient-bootstrap CI | patients in paired change | cannot reach cap (of patient-seeds) |
|---|---|---|---|---|---|
| fp32 | 0.361 | n/a | n/a | n/a | 25/70 |
| int8 | 0.216 | 0.000 | [-0.333, 0.000] | 11 | 16/70 |
| sim6 | 0.079 | 0.000 | [-0.500, 0.000] | 10 | 24/70 |
| sim4 | 0.081 | 0.000 | [-1.000, 0.000] | 10 | 18/70 |
| qat8 | 0.231 | 0.000 | [-0.250, 0.000] | 10 | 25/70 |

## Cap: 1 false alarms per 24 h

| model | pooled sensitivity (median over seeds) | paired change vs FP32 (median of patients) | 95% patient-bootstrap CI | patients in paired change | cannot reach cap (of patient-seeds) |
|---|---|---|---|---|---|
| fp32 | 0.361 | n/a | n/a | n/a | 25/70 |
| int8 | 0.216 | 0.000 | [-0.333, 0.000] | 11 | 16/70 |
| sim6 | 0.079 | 0.000 | [-0.500, 0.000] | 10 | 24/70 |
| sim4 | 0.081 | 0.000 | [-1.000, 0.000] | 10 | 18/70 |
| qat8 | 0.231 | 0.000 | [-0.250, 0.000] | 10 | 25/70 |

## Cap: 2 false alarms per 24 h

| model | pooled sensitivity (median over seeds) | paired change vs FP32 (median of patients) | 95% patient-bootstrap CI | patients in paired change | cannot reach cap (of patient-seeds) |
|---|---|---|---|---|---|
| fp32 | 0.361 | n/a | n/a | n/a | 21/70 |
| int8 | 0.216 | 0.000 | [-0.333, 0.000] | 11 | 16/70 |
| sim6 | 0.079 | 0.000 | [-0.500, 0.000] | 10 | 23/70 |
| sim4 | 0.081 | 0.000 | [-1.000, 0.000] | 10 | 18/70 |
| qat8 | 0.231 | 0.000 | [0.000, 0.000] | 11 | 24/70 |

