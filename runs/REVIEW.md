# Pre-Stage-0 code review (Oct 24, 2026)

Scope: every module on the Stage 0 path (`src/chbmit.py`, `src/pipeline.py`, `src/quantize.py`, `src/scoring.py`, `src/frontier.py`, `scripts/run_patient.py`, `scripts/analyze_frontier.py`), checked for leakage between train, validation and test data and for bugs, with the data-dependent checks run on the real CHB-MIT files.

## Leakage: none found

| Data use | Source | Verdict |
|---|---|---|
| Training windows (seizure + sampled background) | training-fold records only | clean |
| Per-channel normalization (mean, std) | training windows | clean |
| Early stopping | validation-fold records (4 s grid) | clean |
| Thresholds, every model | validation-fold records, seizure-free windows | clean |
| Quantization calibration (ONNX INT8 and simulated) | 2,000 training windows | clean |
| Test records | scoring only | clean |
| Filtering | causal, per record, no look-ahead | clean |

Split unit is the record, as the plan specifies; records of one patient on either side of a split can be adjacent in time, which the record-wise design accepts (no window is shared). For the cross-patient arm: chb21 is the same subject as chb01 and must stay on the same side of every split (README).

## Bugs fixed

| # | Bug | Effect | Fix | Test |
|---|---|---|---|---|
| 1 | Latency was read off SzCORE's **merged** alarms: a false alarm up to 90 s before a seizure merged with the real detection and counted as an early detection | Fake latencies of -30 s, concentrated where false alarms are dense: it would make noisier (more quantized) models look faster, biased against H1 | Latency from raw alarms vs annotated seizures; SzCORE still counts detections and false alarms | `test_false_alarm_before_seizure_is_not_an_early_detection` |
| 2 | Latency was read off SzCORE's **split** seizures: a seizure over 300 s got extra latencies from artificial onsets | Affects chb11_99 (752 s), the only seizure over 300 s | Same fix: one latency per annotated seizure | `test_long_seizure_gets_one_latency_from_its_true_onset` |
| 3 | chb17's records (`chb17a_*` etc.) were not found | 3 seizures and one patient silently missing | Match any record suffix | (count check: 198 seizures) |
| 4 | Records without the temporal channels still got folds | 3 chb12 folds with no seizure to test | Folds built from usable records only; at least 3 seizure records required | `test_make_folds_needs_three_seizure_records` |
| 5 | Signal cache not tied to the preprocessing | A changed filter would silently reuse old signals | Cache folder named by `PREP_TAG` | |
| 6 | Pooled endpoint was a median over all patient-seed values | Did not match the pre-registration | Median over seeds per patient, then over patients; kill rule evaluated on INT8, sim6, sim4 | `test_pooled_excess_is_median_of_patient_medians` |
| 7 | FP32 missing half a patient's seizures gave excess = inf - inf | Counted as censored instead of undefined | Returned as undefined (nan) and counted separately | in `test_excess_latency_interpolates_along_frontier` |

## Checked and fine

- Filter start-up: CHB-MIT records are near zero-mean (DC under 20 uV), so the causal filter has no start-up artifact (first 4 s window within normal amplitude).
- float16 cache: temporal channels span +/-2000 uV, far inside float16; rounding about 1 uV at the extremes.
- Labels: summary files and `.seizures` annotation files agree on all 141 seizure records except chb24_21's onset (2804 vs 2404 s); summary used, as in SzCORE. `RECORDS-WITH-SEIZURES` lists chb07_18 for chb07_19's seizure (not used).
- Folds: every patient has at least 3 usable seizure records; 138 folds in total.
- BatchNorm folding exact; ONNX FP32 export matches PyTorch to 5e-6; INT8 and simulated 8-bit both track FP32 (tests).
- Determinism: re-running a job in the same environment reproduces every number (Linux CPU; DirectML).

## Verification

18/18 tests pass. The chb01 pilot was re-run with the reviewed code (`runs/pilot_chb01_v2`, same pinned WSL environment) and compared job by job with the pre-review run (`runs/pilot_chb01_v1`):

- identical in all 21 jobs: thresholds, window metrics, raw scores of every model, SzCORE detection and false-alarm counts;
- 46 frontier rows changed latency, all later than before (old values mostly the fake -30 s), none at the 12 s operating point, so the pilot's endpoint values are unchanged: INT8 -0.13 s, sim6 -0.55 s, sim4 0.81 s pooled, against a seed null of -0.56 to 0.86 s.

## Follow-up (same day)

- **Saved weights.** Each job's `.npz` now holds the trained FP32 weights and normalization (`pipeline.load_fp32`) and the QAT state. Rebuilding FP32 from a saved job and re-scoring its test records reproduces the saved scores exactly.
- **Quantization-aware training** built (`quantize.QAT`, `qat8`): 8-bit fine-tuning from the job's FP32 model with BatchNorm folded, straight-through gradients, EMA activation ranges. Tests: before training it equals simulated 8-bit exactly; gradients reach the weights; weights stay on the per-channel 8-bit grid. On chb01 fold 0 seed 0 it stopped early after 25 epochs (54 s).
- **Thread count changes results.** The same job at 4 and at 8 CPU threads trained slightly different FP32 models (83 vs 82 epochs; test-score correlation 0.995), from floating-point summation order. At the same thread count (4) the job with QAT reproduces pilot v2 exactly for FP32 and every post-training model. Stage 0 must use one `--threads` value throughout (each job records it).
- 20/20 tests pass.

## Later-stage build (same day)

- Pipeline generalized over dataset (`chbmit`, `siena`, `seizeit2`), model (`epidenet`, `ahlawat`) and arm (patient-specific, cross-patient). Verified bit-identical to pilot v2 on chb01 fold 0 seed 0 (thresholds, validation and test scores, frontier, window metrics).
- Smoke runs (3-epoch training): cross-patient arm, Siena PN05 and SeizeIT2 sub-001 all run end to end; Ahlawat's model on chb01 fold 0 seed 0 runs in full (87 epochs, 56 min per job).
- **Bug 8: threshold ties.** Quantized models output few distinct scores (INT8: about 130). A window was positive at score >= threshold, so validation windows tied at the threshold quantile all alarmed: a collapsed 4-bit Ahlawat model (90% of validation negatives on one value) reached validation specificity 0.10 instead of 0.995, and EpiDeNet-sized INT8 models fall slightly below target. Now positive only at score > threshold (`pipeline.alarm_raw`), which keeps validation specificity at or above target; test `test_threshold_keeps_specificity_with_tied_scores`. FP32 scores are continuous, so FP32 pilot results are unaffected; the pilot's INT8 numbers were computed under the old rule and Stage 0 will use the new one.
- Data findings: Siena's seizure lists needed two documented corrections (PN01 file name; PN00-3 end time); only 8 of 14 Siena patients have the 3+ seizure records the fold design needs. SeizeIT2 recordings use three different two-channel pairs; each subject uses its main pair (53 subjects qualify).
- 26/26 tests pass.
