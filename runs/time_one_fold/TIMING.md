# Week-1 measurement: one patient-specific EpiDeNet fold

> Superseded for results by `runs/stage0/` (Oct 24). These runs used a 4 s evaluation hop and timed alarms at the start of each window, which understates latency by about 4 s; the pipeline now uses a 1 s hop and times alarms at the window's end. The timing figures below still hold for FP32 training alone.

WSL2 Ubuntu, 8 CPU threads, PyTorch 2.14 CPU. Patient chb01 (42 records, 7 seizure records, so 7 folds). Seed 0.
Code: `scripts/time_one_fold.py` -> `src/pipeline.py`. Full output in the `.log` and `.json` files here.
Epoch cap 300, early stopping after 10 epochs without validation-loss improvement.

| | Fold 0 | Fold 1 |
|---|---|---|
| Training (4,180 windows, 380 seizure) | 260 s, early stop at epoch 123, 2.1 s/epoch | 220 s, early stop at epoch 105, 2.1 s/epoch |
| Threshold + test inference + SzCORE scoring | 2 s | 2 s |
| **Total per fold (patient already cached)** | **265 s** | **224 s** |
| Seizures detected | 1/1, latency 8 s | 1/1, latency 1 s |
| False alarms | 4 in 5.7 h (16.7 per 24 h) | 1 in 6.0 h (4.0 per 24 h) |
| Window AUROC / AUPRC | 0.9986 / 0.873 | 0.9999 / 0.940 |
| Test window specificity | 0.9911, within 0.995 +/- 0.005 | 0.9978, within 0.995 +/- 0.005 |

Reading, filtering and caching a patient's records from /mnt/c is a one-time cost: 136 s for chb01's 42 records.

**Per fold: about 4.1 min** (average of the two). Stage 0 estimate: 129 seizure-record folds x 3 seeds = 387 FP32 runs, about 26 h; the same again for quantization-aware training, so about 53 h in total (the plan assumed 39 h at 3 min per fold), plus about 1 h of one-time caching. Fold time scales with a patient's seizure windows, so patients with much more seizure time (e.g. chb12, chb15) will run longer than chb01.

## History

- First run with a 100-epoch cap: both folds hit the cap with validation loss still falling (fold 0: 176 s, test specificity 0.9891, outside the band). Raising the cap to 300 lets early stopping fire on its own.
- Fold 1 gives identical results under both caps: its best epoch (95) came before epoch 100, and the run is deterministic for a fixed seed.

## Flags for the pre-registration

- **Tolerance band:** test window specificity must land within TARGET_SPEC +/- SPEC_TOLERANCE (0.995 +/- 0.005). A fold outside it is flagged (`spec_in_band: false`) and reported, never re-thresholded on test data.
- **Validation is thin on seizures:** the validation records hold only 7 to 10 seizure windows, so validation loss (and the early-stopping epoch) mostly tracks background windows.
