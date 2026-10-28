# Why the FP32 sanity gate failed (post hoc investigation, Oct 26-27, 2026)

All checks use Stage 0's saved scores; no model was retrained. Everything here is post hoc and exploratory.

| Hypothesis | Test | Verdict |
|---|---|---|
| Thresholds set on one validation fold transfer to test with a systematic downward bias (e.g. early stopping and thresholds share the validation fold) | Distribution of per-job test specificity against the 0.995 target | **Rejected.** Median test specificity is exactly 0.9950 for every model (50-51% of jobs below target). The pooled mean (0.991) is pulled down by a heavy lower tail: 25% of jobs fall below 0.990. |
| A few recordings dominate the false positives | Share of voted false-positive windows by test record | **Confirmed.** The worst 1% of record-seed pairs carry 57% of voted false-positive windows; the worst 10% carry 87%. Worst records: chb09_11, chb07_14, chb04_19, all 4 h seizure-free recordings. |
| Those recordings contain a technical artifact (flat or disconnected channel, saturation) | Signal statistics of 4 s windows where the model fires | **Rejected.** No flat channels; saturation in at most 7% of firing windows. Firing windows show 5-15x the baseline amplitude (channel SD about 150-370 uV, peaks about 950 uV) for minutes at a time: high-amplitude physiological or movement activity, which a technical artifact filter would not remove. |
| EpiDeNet's 2.24 FP/h was measured on seizure-containing records only (its LOOCV validates on the excluded seizure record), a different population from ours | Voted window FP/h on seizure vs seizure-free records | **Rejected.** On seizure records our rate is higher (8.32/h; windows next to seizures), on seizure-free records 5.24/h, overall 5.83/h. |
| The reimplementation matches EpiDeNet's operating curve but sits at a more sensitive point | Detection and voted FP/h at stricter validation targets | **Rejected in part.** At a target giving EpiDeNet's voted specificity (0.999 -> 0.9978), detection is 80.4% vs EpiDeNet's 91.2%. Both gate parts pass only at targets 0.9975-0.998 (detection 86-87%, 3.2-3.8 FP/h). |

## Conclusion

The gate failed because the reimplementation is weaker than published EpiDeNet at matched specificity (about 11 points lower detection), with false positives concentrated in a few long seizure-free recordings with high-amplitude non-seizure activity. It is not a threshold-transfer defect, so changing the threshold protocol until the gate passes would be tuning to the gate. Plausible sources of the gap, from the stated implementation differences: class-weighted cross-entropy instead of EpiDeNet's SSWCE loss; the assumed channel set and filter; and training data (EpiDeNet's LOOCV trains on every other seizure record, while this design also holds out a validation fold, which for a 3-seizure-record patient leaves one training seizure).
