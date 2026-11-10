# Fidelity check and OSF registration update (draft, not yet registered or run)

Revised 2026-11-10 after advisor review (S. Aryal): Stage 0 is reported as exploratory whatever the check shows; the check now decides only which model later stages use. Added: an exploratory recall-at-false-alarm-cap analysis, and a hardware framing for the bit widths.

## What EpiDeNet actually did on CHB-MIT (from the paper)

- **Loss.** SSWCE (sensitivity-specificity weighted cross-entropy) was introduced and tuned per patient by grid search on **PEDESITE** (Table III has separate "EEG" and "EEG + SSWCE" columns). Table II (CHB-MIT) has no SSWCE column, so the CHB-MIT results were evidently trained without it. Adding SSWCE would therefore *not* move the reimplementation closer to the CHB-MIT numbers the gate compares against; it is not part of the fix.
- **Protocol.** "We train on all records containing seizures except for one, and validate using the excluded record." Training uses seizure-containing records only; evaluation is on the one excluded seizure record; there is no separate validation fold and no tuned threshold (none is described; most likely the default decision of the 2-class output).
- **Unstated:** optimizer, learning rate, epochs, class weighting, filtering, which temporal channels.

## Why this matters for the failed gate

The registered gate compared numbers from **this study's protocol** (training on all non-test, non-validation folds including seizure-free records; thresholds at 0.995 validation specificity; evaluation over all held-out hours, including long seizure-free recordings) with numbers from **EpiDeNet's protocol** (seizure records only, default decision, evaluation on seizure records). A reimplementation check has to compare like with like. The post hoc investigation (runs/stage0/GATE_INVESTIGATION.md) found the false positives concentrated in long seizure-free recordings, which EpiDeNet's protocol never evaluates; it also found higher false-positive rates on seizure records under this study's thresholds, so the mismatch may not explain the whole gap. Only a protocol-matched run can say.

## Proposed update (register on OSF before running anything below)

1. **The registered gate stays failed and is reported.** Nothing in this update changes that result.
2. **Stage 0 is reported as exploratory.** Its results were seen before this update, and the registered gate failed; no outcome of the check below makes them confirmatory. All Stage 0 numbers (primary endpoint, stop rule, H2, H3) are reported as registered, labelled exploratory.
3. **Added: a protocol-matched reimplementation check (FP32 only).** For every CHB-MIT patient, leave-one-seizure-record-out exactly as EpiDeNet describes: train on all other seizure-containing records (temporal-4 channels, same preprocessing and architecture), evaluate on the excluded seizure record, positive window = model's predicted class (default decision, no threshold tuning), EpiDeNet's 2-of-3 vote on 4 s windows. 3 seeds. Pass criteria: the registered rule unchanged (detection >= 82.3% of usable seizures; voted window FP/h within 1.12-4.48).
   - Training length (no validation fold in EpiDeNet's protocol): early stopping on a random 25% of the training windows, stratified by class and drawn with the job's seed, held out from gradient updates; the remaining 75% train the model. Same early-stopping rule as Stage 0 (patience 10 epochs, at most 300, best epoch kept). Those windows come from the same training records, so this only chooses the stopping epoch; the excluded test record is never used for it.
4. **Decision rule, fixed in advance (what the check decides):**
   - If the check **passes**, the reimplementation is taken to reproduce EpiDeNet, and EpiDeNet stays the primary model for later stages.
   - If it **fails**, the reimplementation does not reproduce EpiDeNet; per the original plan, recheck Table I against the code, and if still off, make Ahlawat's model primary for later stages and say so.
   - Either way, the result is reported with the failed registered gate and the investigation.
5. **Added (exploratory): recall at a false-alarm cap.** A missed seizure costs more than a false alarm, but false alarms must stay low enough for human follow-up. For each patient, seed and model, on the existing Stage 0 frontiers (no new training): sensitivity = detected / annotated seizures (SzCORE event scoring) at the smoothing width with the highest sensitivity among those whose false alarms per 24 h are at or below the cap; ties go to the smaller width. No interpolation (event counts are discrete).
   - Caps: 0.5, 1 and 2 false alarms per 24 h.
   - Reported per model: pooled sensitivity at each cap (all patients' seizures summed, median over seeds); paired change vs the same seed's FP32 (patient bootstrap, 95% interval); the number of patient-seed values where the model, or FP32, cannot reach the cap at any width (reported, not imputed).
   - Labelled exploratory: Stage 0's frontiers have already been seen, though this quantity has not been computed.
6. **Reporting the bit widths against hardware.** INT8 is the deployed case (native on Cortex-M with CMSIS-NN, GAP8/GAP9; EpiDeNet's own deployment). Simulated 6- and 4-bit quantize both weights and activations; mainstream microcontrollers have no native arithmetic below 8 bits, so these are reported as stress points that locate where the trade-off starts to move, not as deployment scenarios.
7. **Not changed:** the primary endpoint, stop rule, thresholds and evaluation of the quantization study.

## Implementation (when you say go)

- `records.loocv_seizure_folds(records)`: one fold per seizure record; training = the other seizure records; seizure-free records unused.
- `pipeline.run_reimplementation_check(...)`: FP32 training only, default decision, EpiDeNet's metrics; no quantization, no frontier.
- `scripts/run_gate_check.py` (138 folds x 3 seeds; FP32 only, so about a third of a Stage 0 job each) and `scripts/sanity_gate.py --protocol epidenet`.
- `frontier.sensitivity_at_cap(frontier, cap)` and a `--caps` section in `scripts/analyze_stats.py` for item 5.
- Tests for the fold builder, the default-decision path and the cap selection; a smoke run checked for errors only, with no metrics inspected, before registration.

Estimated compute: about 4-6 hours for the check (no quantized models, no frontier sweeps); item 5 reuses Stage 0's saved frontiers and needs minutes.
