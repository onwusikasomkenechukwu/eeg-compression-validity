# Recall at a false-alarm cap (exploratory): runs/stage1_ahlawat_ws_bitwidths

24 patient(s), 120 patient-seed values per model. SzCORE event sensitivity at the smoothing width with the most detected seizures among those with false alarms per 24 h at or below the cap.

## Cap: 0.5 false alarms per 24 h

| model | pooled sensitivity (median over seeds) | paired change vs FP32 (median of patients) | 95% patient-bootstrap CI | patients in paired change | cannot reach cap (of patient-seeds) |
|---|---|---|---|---|---|
| fp32 | 0.656 | n/a | n/a | n/a | 83/120 |
| int8 | 0.658 | 0.000 | [0.000, 0.000] | 13 | 79/120 |
| sim6 | 0.594 | 0.000 | [0.000, 0.000] | 12 | 79/120 |
| sim4 | 0.300 | 0.000 | [0.000, 0.000] | 12 | 61/120 |
| w4a8 | 0.686 | 0.000 | [0.000, 0.000] | 13 | 82/120 |
| fp16 | 0.600 | 0.000 | [0.000, 0.000] | 13 | 84/120 |

## Cap: 1 false alarms per 24 h

| model | pooled sensitivity (median over seeds) | paired change vs FP32 (median of patients) | 95% patient-bootstrap CI | patients in paired change | cannot reach cap (of patient-seeds) |
|---|---|---|---|---|---|
| fp32 | 0.582 | n/a | n/a | n/a | 54/120 |
| int8 | 0.581 | 0.000 | [0.000, 0.000] | 17 | 53/120 |
| sim6 | 0.570 | 0.000 | [0.000, 0.000] | 17 | 52/120 |
| sim4 | 0.346 | 0.000 | [-0.200, 0.000] | 17 | 32/120 |
| w4a8 | 0.633 | 0.000 | [0.000, 0.000] | 17 | 54/120 |
| fp16 | 0.582 | 0.000 | [0.000, 0.000] | 17 | 54/120 |

## Cap: 2 false alarms per 24 h

| model | pooled sensitivity (median over seeds) | paired change vs FP32 (median of patients) | 95% patient-bootstrap CI | patients in paired change | cannot reach cap (of patient-seeds) |
|---|---|---|---|---|---|
| fp32 | 0.608 | n/a | n/a | n/a | 33/120 |
| int8 | 0.611 | 0.000 | [0.000, 0.000] | 20 | 30/120 |
| sim6 | 0.609 | 0.000 | [0.000, 0.000] | 19 | 32/120 |
| sim4 | 0.388 | 0.000 | [-0.121, 0.000] | 20 | 18/120 |
| w4a8 | 0.598 | 0.000 | [0.000, 0.000] | 20 | 31/120 |
| fp16 | 0.608 | 0.000 | [0.000, 0.000] | 20 | 33/120 |

