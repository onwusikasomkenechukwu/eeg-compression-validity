# Recall at a false-alarm cap (exploratory): runs/stage2_siena

8 patient(s), 40 patient-seed values per model. SzCORE event sensitivity at the smoothing width with the most detected seizures among those with false alarms per 24 h at or below the cap.

## Cap: 0.5 false alarms per 24 h

| model | pooled sensitivity (median over seeds) | paired change vs FP32 (median of patients) | 95% patient-bootstrap CI | patients in paired change | cannot reach cap (of patient-seeds) |
|---|---|---|---|---|---|
| fp32 | 0.500 | n/a | n/a | n/a | 30/40 |
| int8 | 0.250 | 0.000 | [-0.250, 0.000] | 3 | 29/40 |
| sim6 | 0.154 | -0.250 | [-0.250, 0.000] | 3 | 25/40 |
| sim4 | 0.087 | -0.250 | [-0.500, 0.000] | 3 | 21/40 |
| qat8 | 0.250 | 0.000 | [-0.250, 0.000] | 3 | 29/40 |

## Cap: 1 false alarms per 24 h

| model | pooled sensitivity (median over seeds) | paired change vs FP32 (median of patients) | 95% patient-bootstrap CI | patients in paired change | cannot reach cap (of patient-seeds) |
|---|---|---|---|---|---|
| fp32 | 0.500 | n/a | n/a | n/a | 30/40 |
| int8 | 0.250 | 0.000 | [-0.250, 0.000] | 3 | 29/40 |
| sim6 | 0.154 | -0.250 | [-0.250, 0.000] | 3 | 25/40 |
| sim4 | 0.087 | -0.250 | [-0.500, 0.000] | 3 | 21/40 |
| qat8 | 0.250 | 0.000 | [-0.250, 0.000] | 3 | 29/40 |

## Cap: 2 false alarms per 24 h

| model | pooled sensitivity (median over seeds) | paired change vs FP32 (median of patients) | 95% patient-bootstrap CI | patients in paired change | cannot reach cap (of patient-seeds) |
|---|---|---|---|---|---|
| fp32 | 0.462 | n/a | n/a | n/a | 26/40 |
| int8 | 0.261 | -0.100 | [-0.250, 0.000] | 4 | 24/40 |
| sim6 | 0.308 | -0.225 | [-0.250, 0.000] | 4 | 22/40 |
| sim4 | 0.077 | -0.250 | [-0.600, 0.000] | 4 | 18/40 |
| qat8 | 0.500 | 0.000 | [-0.250, 0.000] | 4 | 24/40 |

