# OSF Preregistration: text for each page of the form

Paste each block into the matching field. Code referenced: https://github.com/onwusikasomkenechukwu/eeg-compression-validity at commit 3a9b77d.

---

## Page 1: Metadata

**Title**

> Does post-training quantization delay seizure alarms? A pre-registered test of the false-alarm/latency frontier of a compressed EEG seizure detector

**Description**

> Compressed (quantized) seizure detectors are certified with window-level metrics such as AUROC, sensitivity and specificity. These metrics ignore time order, so they cannot show whether compression changes what a deployed detector does over time: how many false alarms it raises and how late it alarms. Every detector trades fewer false alarms for later detection through post-processing (smoothing). We test whether quantization moves a detector along this trade-off: to match its full-precision (FP32) parent's false alarms, does a quantized detector need more smoothing and therefore alarm later? We reimplement EpiDeNet (Ingolfsson et al. 2023), train patient-specific models on CHB-MIT, quantize each trained model after training (ONNX Runtime INT8; simulated 6- and 4-bit), and compare every quantized model with its own FP32 parent on SzCORE event scoring. The primary outcome is the excess median detection latency, in seconds, that INT8 needs to match FP32's false alarms per 24 hours. A stop rule, fixed here, ends the project if no quantized model clears both the seed-to-seed noise of FP32 training and a 2-second floor. This is an evaluation-validity study, not a clinical-readiness claim.

**Contributors:** you (add your advisor if they should be a contributor).

**Affiliated institutions:** Howard University, if it appears in OSF's list.

**License:** CC-By Attribution 4.0 International (people can reuse the text if they credit you). CC0, the default, is also fine.

**Subjects:** Engineering > Biomedical Engineering and Bioengineering; Physical Sciences and Mathematics > Computer Sciences > Artificial Intelligence and Robotics; Medicine and Health Sciences > Medical Specialties > Neurology.

**Tags:** seizure detection, EEG, epilepsy, model compression, quantization, false alarms, detection latency, CHB-MIT, SzCORE, evaluation validity, wearable devices, TinyML

---

## Page 2: Overview (Study information)

**Hypotheses**

> H1 (frontier shift, primary). At FP32's operating point, post-training INT8 needs more detection latency to reach FP32's false alarms per 24 hours; equivalently, at FP32's latency it raises more false alarms.
>
> H2 (dose-response). The latency shift grows as bit-width falls from 8 to 6 to 4 bits.
>
> H3 (mechanism). Quantization error is weakly correlated in time, so each patient's shift scales with the fraction of time that patient's FP32 scores spend near the decision threshold (dwell). Dwell is measured on the FP32 model before any quantization, so H3 is a prediction, not a fit.
>
> Only H1's INT8 test is confirmatory. Every other comparison is exploratory and will be labeled so.

---

## Page 3: Research Design (Design plan)

**Study type:** Other (computational study on existing public data). Explain:

> A computational experiment on publicly available, de-identified EEG recordings. No participants are recruited and no new data are collected.

**Blinding:** No blinding is involved in this study.

**Study design**

> Model: EpiDeNet reimplemented from Table I of Ingolfsson et al. 2023 (4 temporal bipolar channels F7-T7, T7-P7, F8-T8, T8-P8; 4 s windows at 256 Hz). The reimplementation matches the paper's operation count (2,053,410 vs 2,053,516 MACs).
>
> Patient-specific arm (confirmatory). For each patient, one fold per seizure record; seizure-free records are dealt round-robin across folds. Fold k is tested, fold k+1 validates (early stopping and thresholds), the rest train. Records are never split, so no window is in two sets.
>
> Paired comparison. In each fold and seed, one FP32 model is trained; every compressed model is built from that same trained model after training: ONNX Runtime static INT8 (per-channel symmetric weights, per-tensor activations, MinMax calibration on 2,000 training windows; the primary condition), and simulated 8-, 6- and 4-bit quantization (per-channel weights, per-tensor activations, BatchNorm folded). Quantization-aware 8-bit training (fine-tuned from the FP32 model) is run too, but because retraining mixes quantization with training noise it is compared only with the seed-noise null, not as a paired test.
>
> Operating points. Each model's threshold is set to window-level specificity 0.995 on the validation records' seizure-free windows; a window is positive only when its score is strictly above the threshold.
>
> Evaluation. Windows every 1 s. Smoothing: an alarm is on when more than half of the windows ending in the last W seconds are positive (causal); W = 12 s is the default (EpiDeNet's three-window majority vote); the frontier sweeps W = 4, 8, 12, 16, 20, 24, 30, 36, 45, 60, 75, 90, 120 s. An alarm is timed at the end of its window. Events are scored with SzCORE (30 s pre-ictal and 60 s post-ictal tolerance, merge within 90 s, split over 300 s), giving false alarms per 24 h and detected seizures.
>
> Latency: seconds from the annotated onset to the first raw alarm overlapping the seizure's tolerance window, measured on the raw alarms and annotated seizures (not SzCORE's merged or split events); negative inside the 30 s pre-ictal tolerance; a missed seizure is censored.
>
> Seeds: 3 training seeds per fold (0, 1, 2).

**Randomization:** No randomization of participants. Random elements (training initialization, background-window sampling, calibration subset, batch order) are fixed by the seed.

---

## Page 4: Sampling

**Existing data:** choose **"Registration following analysis of the data"** (the accurate option: one patient was analyzed as a pilot). Explanation:

> All three datasets are public and were downloaded before registration. One CHB-MIT patient (chb01: 7 folds x 3 seeds, 21 jobs) was analyzed as a pilot to build and debug the pipeline (the "pipeline gate"). Decisions made after the pilot, disclosed here: the primary endpoint is interpolated along each model's frontier (not the least smoothing at or above 12 s); the specificity check is pooled per patient (not per fold); the epoch cap was raised from 100 to 300; latency is measured on raw alarms, not SzCORE's merged events (a bug fix); and a window is positive only when its score is strictly above the threshold (a bug fix for quantized models' tied scores, found on a test run of the secondary model). Pilot results, computed before the last fix: INT8 excess latency -0.13 s, 6-bit -0.55 s, 4-bit 0.81 s against a seed null of -0.56 to 0.86 s. No other patient has been trained or scored. Label counts and recording metadata were computed for all datasets (to define folds and exclusions). chb01 stays in the confirmatory analysis.

**Data collection procedures**

> CHB-MIT Scalp EEG (PhysioNet chbmit 1.0.0, ODC-By 1.0): 24 pediatric cases, chb01-chb24 (chb21 is chb01 recorded 1.5 years later), 686 records, 198 seizures, 256 Hz, verified against PhysioNet's SHA-256 checksums. Seizure times from the summary files (as in SzCORE's converter).

**Sample size**

> 683 records with the four temporal channels (three chb12 records use another montage), 185 seizures, 138 seizure records, so 138 folds; 3 seeds gives 414 FP32 models, each with its paired quantized models.

**Sample size rationale**

> The whole public dataset is used; no power analysis. With 24 cases (23 independent patient groups), results are reported as effect sizes with patient-bootstrap intervals; p-values are secondary.

**Stopping rule**

> All 414 jobs are run. No interim analysis of patients beyond the chb01 pilot.

---

## Page 5: Variables

**Manipulated variables**

> Model precision: FP32 (reference); post-training INT8 (ONNX Runtime, primary); simulated 8-, 6- and 4-bit post-training quantization; quantization-aware 8-bit (secondary). Smoothing width W (4-120 s), swept to trace each model's frontier.

**Measured variables**

> Per patient, seed and model, pooled over the patient's held-out records: SzCORE false alarms per 24 h; detected seizures (counts); latency per seizure. Window level: AUROC, AUPRC, specificity. EpiDeNet-comparable: window false positives per hour on the 4 s grid, raw and with the 3-window vote; seizures with at least one voted-positive window inside them. H3: dwell (share of FP32 test windows within 0.5 logits of the FP32 threshold); autocorrelation over time of (quantized - FP32) logits.

**Indices**

> Median latency treats a missed seizure as infinitely late (censored). Excess latency (primary): FP32's operating point is its 12 s smoothing, giving false alarms FA0 and median latency L0; a quantized model's latency at exactly FA0 is read off its frontier (false alarms vs median latency across smoothing widths) by linear interpolation, taking the lowest latency where the curve crosses FA0 more than once; excess = that latency - L0. If the model never comes down to FA0, the excess is +infinity (censored); if it is below FA0 even at 4 s smoothing, its 4 s latency is used. Patient value: median over seeds; pooled value: median over patients.

---

## Page 6: Analysis Plan

**Statistical models**

> Primary test: pooled excess latency of post-training INT8 against the FP32 seed-noise null. The null is the same excess-latency computation between two FP32 seeds of the same patient, for every ordered seed pair, pooled across patients; its 95% band is the 2.5th-97.5th percentile. Effect sizes with 95% patient-bootstrap intervals (2,000 resamples). Linear mixed-effects model: excess latency ~ 1 + (1 | patient) on patient-seed values, per model (as in Reisinger et al. 2025). Concentration: share of the summed shift carried by the worst 20% of patients. H3: Spearman correlation across patients between FP32 dwell and the patient's median excess latency.

**Transformations**

> None beyond those defined in Indices. Signals: causal 0.5-40 Hz band-pass; per-channel standardization from training windows.

**Inference criteria**

> Stage 0 stop rule. The project stops if, for each of INT8, 6-bit and 4-bit, the pooled excess latency lies inside the FP32 null band or is below 2 s. If INT8 is stopped but 6-bit or 4-bit is not, the paper reports where compression starts to cost latency.
>
> The 2 s floor separates a real shift from one too small to matter: it is about a quarter of typical latency (8 s on the pilot; 9 s for the wearable EMG detector of Beniczky et al. 2018), two steps of the 1 s decision grid, and a little over twice the pilot null's upper edge.
>
> FP32 sanity gate (reimplementation check, decided before the primary test), using EpiDeNet's own definitions and pooled over all patients, averaged over seeds; both parts must pass: (A) seizures detected >= 82.3% of usable seizures (>= 153 of 185), which is EpiDeNet's 8.8% miss rate (165/181) doubled; (B) voted window false positives per hour within [1.12, 4.48], i.e. EpiDeNet's 2.24 within a factor of 2 (window specificity 0.99502-0.99876). EpiDeNet's FP/h counts misclassified 4 s windows, not alarms, so this is compared in its unit. A failure means the reimplementation is wrong, not the hypothesis.
>
> Specificity check: per patient and seed, FP32 test window specificity pooled over all held-out hours must be within 0.995 +/- 0.005; results outside it are reported, never re-thresholded on test data.

**Data exclusion**

> Records without the four temporal channels are excluded (three chb12 records, 13 seizures). Patients need at least three usable seizure records (all CHB-MIT patients qualify). No exclusion based on results.

**Missing data**

> A missed seizure is a censored latency (infinitely late), never dropped. If FP32 itself misses half or more of a patient's seizures, that patient's excess latency is undefined and is reported separately, not counted as censored.

**Exploratory analysis**

> Everything except H1's INT8 test: 6- and 4-bit (H2), quantization-aware training, the reused-FP32-threshold (calibration) result, false alarms at FP32's latency (the second form of H1), H3, window-counted FP/h vs SzCORE false alarms per patient, a 25%-of-latency relative floor, and a robustness rerun of seed 0 for every patient on a GPU. Later stages (5 seeds; Ahlawat's 1D CNN; a leave-one-patient-group-out arm with chb01 and chb21 kept together; Siena replication with the 8 patients that have 3+ seizure records; a SeizeIT2 subset) are exploratory relative to this registration.

---

## Page 7: Other

> Computational environment: WSL2 Ubuntu, Python 3.12, torch 2.14.1 (CPU), package versions in requirements.txt, 4 threads per job. Device, library versions and thread count change floating-point summation order and so change trained models slightly; within this environment every job is bit-for-bit reproducible, and each job saves its trained weights, normalization and scores. Analysis code: commit 3a9b77d of the repository above; scripts/run_patient.py runs the jobs, scripts/analyze_frontier.py applies the stop rule, scripts/analyze_stats.py the statistics. An audit of 14 papers that compress a seizure detector found none that compares event-level false alarms or latency before and after compression.

---

## Page 8: Review

Check each page, then choose **"Enter into embargo"** with an end date after the planned submission (e.g. mid-2027), and submit. The registration cannot be edited or deleted afterwards.
