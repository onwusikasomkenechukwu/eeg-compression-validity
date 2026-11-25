# Why the Siena fidelity check failed (post hoc, exploratory, not registered)

Fidelity check B (update 6) requires FP32 test window specificity, pooled over all of a patient's held-out hours, within 0.995 +/- 0.005 for at least two thirds of patient-seed values. Siena: 12/40 in the patient-specific arm, 34/70 in the cross-patient arm (CHB-MIT: 87/120). This note looks at why. It changes no registered decision. Computed from the saved scores and summaries (scripts in the session scratchpad; numbers reproducible from `fold*_seed*.npz` / `.json`).

## 1. The thresholds are not biased; they are noisy, and the noise does not average out

Each threshold is set at 0.995 specificity on validation data, and validation specificity at the threshold is 0.9950 (median) in both arms, as designed. Median test specificity is also on target (0.9954 patient-specific, 0.9959 cross-patient). The failure is spread, not shift: single jobs fall within the band in 79/160 and 34/70 (CHB-MIT 470/690), with misses in both directions (patient-specific: 61 jobs below 0.99 and 20 at exactly 1.0; cross-patient: 23 and 13).

## 2. Validation size is not the cause

Validation sets are not small: a median of 8,519 background windows per job in the patient-specific arm and 27,665 in the cross-patient arm. Jobs with smaller-than-median validation sets were no more often outside the band (in band: 0.55 small vs 0.44 large, patient-specific; 0.51 vs 0.46, cross-patient).

## 3. In the patient-specific arm, one recording per patient carries most false positives, in every seed

For each patient and seed, the fold (one test recording) with the most false-positive windows:

| patient | worst recording (seeds 0-4) | its share of the patient's FP32 false-positive windows |
|---|---|---|
| PN00 | PN00-3 in 5/5 | 0.88-0.94 |
| PN05 | PN05-2 in 5/5 | 0.60-0.89 |
| PN06 | PN06-1 in 5/5 | 0.49-0.68 |
| PN09 | PN09-2 in 4/5 | 0.50-0.98 |
| PN10 | PN10-1 in 5/5 | 0.84-0.89 |
| PN12 | varies | 0.46-0.70 |
| PN13 | PN13-2 or -3 | 0.57-1.00 |
| PN14 | PN14-3 in 5/5 | 0.36-0.66 |

So the miss is a property of particular recordings, not of training randomness: a recording whose background looks unlike the patient's other recordings produces sustained above-threshold activity, whatever the seed. This is the same pattern found on CHB-MIT with EpiDeNet (1% of test recordings carried 57% of false-positive windows; `runs/stage0/GATE_INVESTIGATION.md`). On Siena it is worse because each patient has only 3-6 recordings (every recording of these 8 patients contains a seizure, so there are no seizure-free recordings to spread across folds), so one unusual recording is a third to a fifth of the patient's held-out hours.

## 4. The detector separates seizures less well on Siena

Median FP32 test window AUROC: 0.993 on CHB-MIT, 0.916 (patient-specific) and 0.905 (cross-patient) on Siena. The patient-specific arm also trains on about a third of the data (median 1,068 training windows, 152 of them seizure, against 3,223 and 293 on CHB-MIT), but the cross-patient arm trains on far more (27,703 and 2,518) and is no better, so data quantity alone does not explain it. Adult focal seizures (Siena) are plausibly harder for an 18-channel window classifier than CHB-MIT's mostly paediatric seizures, and Siena's bipolar channels are derived from a referential montage, not recorded as bipolar. A flatter score distribution near the threshold makes the threshold's test specificity more sensitive to small shifts in a recording's background.

## 5. Cross-patient arm

The cross-patient arm misses in both directions by patient: some held-out patients produce almost no above-threshold background (specificity 1.0000 in 13 jobs; e.g. PN06 in every seed), others a great deal (PN07 0.02-0.93, PN12 0.79-0.95). A threshold set on one patient's background does not transfer to another's, which is the expected weakness of cross-patient detectors.

## What this means for the paper

- The registered rule is applied as written: both arms are exploratory.
- The failure supports, rather than weakens, the paper's broader point: a fixed operating point set on validation windows does not guarantee the event-level false-alarm rate on new recordings, and the shortfall is concentrated in a few recordings.
- A future Siena test would need either more recordings per patient or a design that holds out recordings, not seizures, with seizure-free hours (as CHB-MIT has); no such change is proposed here.
