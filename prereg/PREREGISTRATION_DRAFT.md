*Superseded: the submitted registration text is `prereg/OSF_FORM.md` (2026-10-25), with updates in `prereg/OSF_UPDATE_FORM.md` and `prereg/OSF_UPDATE_AHLAWAT.md`. Kept as the working draft.*

# Pre-registration draft: the FP32 sanity gate and the Stage 0 latency floor

Draft of Oct 24, 2026, for the OSF registration due Nov 13. It covers the two rules the research plan marks as guesses: the 2x tolerance on the FP32 sanity gate and the 2-second floor in the Stage 0 kill. Everything else is fixed elsewhere: the claim, primary test and gates in the plan, and the implementation choices in the docstrings of `src/chbmit.py`, `src/pipeline.py`, `src/quantize.py` and `src/frontier.py`.

**Pilot disclosure.** One patient (chb01: 7 folds x 3 seeds, 21 jobs) was run before these rules were fixed, as the plan's pipeline gate (`runs/stage0/GATE.md`). Its numbers are quoted below as pilot evidence. No other patient has been trained or scored.

## 1. FP32 sanity gate (Nov 22)

### What the plan says, and the unit problem

The plan asks that the reimplemented EpiDeNet "lands within 2x of its published smoothed rate of 2.24 false alarms per hour". But EpiDeNet's FP/h is not alarms. It counts misclassified 4-second windows per hour: (1 - specificity) x 900 windows per hour. Its Table II pairs 99.52% specificity with 4.29 FP/h (0.0048 x 900 = 4.3) and 99.75% with 2.24 (0.0025 x 900 = 2.25). An event-level false-alarm rate (SzCORE, merging detections within 90 s) is a different quantity: on the chb01 pilot the same model gives 5.7 to 6.4 times fewer SzCORE false alarms per hour than voted window FP/h.

A second problem: this pipeline sets every threshold at a target window specificity of 0.995 on validation hours, which by construction puts raw window FP/h near (1 - 0.995) x 900 = 4.5, almost EpiDeNet's 4.29. So a false-positive check mostly tests whether the threshold transfers from validation to test, not whether the model is right. Whether the model is right shows on the detection side, at that specificity.

### Rule

Computed with EpiDeNet's own definitions (4 s non-overlapping windows; causal 2-of-3 window vote; a seizure counts as detected when at least one voted-positive window lies at least half inside it), pooled over all patients and averaged over the 3 Stage 0 seeds. Both parts must pass.

| Part | Pass if | Derivation | chb01 pilot |
|---|---|---|---|
| **A. Detection** | seizures detected >= **82.3%** of usable seizures (>= 153 of 185) | EpiDeNet detects 165/181 = 91.2%, so it misses 8.8%. "Within 2x" is applied to the **miss rate**, the quantity near its bound: misses <= 17.7%, so detection >= 82.3%. A ratio on detections themselves (anything above 45.6%) would be meaningless. | 20/21 seizure-seed pairs (95%) |
| **B. False positives, EpiDeNet's unit** | voted window FP/h within **[1.12, 4.48]** (2.24 / 2 to 2.24 x 2) | Equivalent to voted window specificity in [0.99502, 0.99876]: from 0.25 percentage points below EpiDeNet's 99.75% to 0.13 above. In specificity terms "2x" is tight, not lenient. | 2.22, 2.52, 2.22 |

**Why 2x, and not tighter.** The reimplementation differs from EpiDeNet in ways the paper does not pin down and that this registration states: which four temporal channels, the band-pass filter, training-window sampling, the loss (class-weighted cross-entropy instead of the SSWCE loss tuned on PEDESITE), the optimizer schedule, 3 seeds instead of 5, and how 185 vs 181 usable seizures arise. Sampling noise alone is smaller: with about 185 seizures, the binomial standard error of a 91% detection rate is about 2.1 points, so the 82.3% bound sits about 4 standard errors below EpiDeNet. The 2x margin is there to absorb the stated implementation differences, not chance. A reimplementation that misses more than twice as many seizures, or whose voted false-positive rate is off by more than a factor of 2, is wrong in some respect that matters for the comparison, and the plan's response applies (recheck Table I; if still off, make Ahlawat's model primary and say so).

**Denominator.** CHB-MIT has 198 annotated seizures in 686 records (141 seizure records). Three chb12 records (13 seizures) use a montage without the four temporal channels and are excluded, leaving 185 usable seizures in 683 records, 138 of them seizure records (so 138 folds; 414 FP32 jobs at 3 seeds). EpiDeNet reports 181 and does not say which were excluded. Seizure times come from the summary files; they disagree with the `.seizures` annotation files only for chb24_21 (onset 2804 s vs 2404 s), and the summary is used, as in SzCORE's converter.

**Reported, not gated:** raw window FP/h (EpiDeNet 4.29; pinned near 4.5 by the threshold protocol), window sensitivity raw and voted (EpiDeNet 68.56% / 68.73%; the chb01 pilot gives 78-94%, an easy patient), and SzCORE false alarms per 24 h.

## 2. Stage 0 kill: the latency floor (Dec 15)

### Rule, stated exactly

For each patient p, seed s and quantized model m (post-training INT8, simulated 6-bit, simulated 4-bit), the excess latency E(p, s, m) is the latency m needs at exactly FP32's false-alarm rate (FP32 at its default 12 s smoothing, same seed), read off m's frontier by linear interpolation (`src/frontier.py`). The patient value is the median over seeds; the pooled value E(m) is the median over patients.

The FP32 null is the same quantity between two FP32 seeds of the same patient, for every ordered seed pair; its 95% band is the 2.5th to 97.5th percentile pooled across patients.

**The project stops** if, for every m, E(m) lies inside the null band **or** E(m) < **2 s**. If INT8 is stopped by the rule but 6-bit or 4-bit is not, the paper becomes where compression starts to cost latency (as in the plan).

### Why a 2-second floor

The band answers "is the shift real?"; the floor answers "is it big enough to matter?". Pooled over 23 patients and 3 seeds the band will narrow, so a statistically clear shift of a fraction of a second becomes possible. The floor keeps such a shift from carrying the paper.

1. **Relative to the latency being shifted.** On the chb01 pilot FP32's median latency at its operating point is 8 s; the clinically validated wearable EMG detector in Beniczky et al. (2018) reports a median of 9 s. Two seconds is about a quarter of either, a change in alarm timing large enough to report on its own.
2. **Relative to measurement resolution.** CHB-MIT annotates every onset and offset in whole seconds (396 of 396 annotation times), and the pipeline makes a decision every 1 s, timed at the end of each 4 s window. The annotation rounding cancels in the paired FP32-vs-quantized difference, but the 1 s decision grid does not: a single seizure's latency difference moves in 1 s steps, and the floor is two of those steps.
3. **Relative to the pilot null.** On chb01 the FP32 seed-pair null runs from -0.6 to 0.9 s (6 ordered pairs). The floor sits at a little over twice the null's upper edge, so it is not redundant with the band at pilot scale, and it becomes the binding rule as the band narrows.

**Alternative considered:** a relative floor (25% of each patient's FP32 median latency). Rejected as the gate because patients with very short FP32 latency would get floors below the 1 s decision grid. It is reported as a secondary analysis.

**Pilot reference (chb01, interpolated):** INT8 -0.1 / 0.2 / -0.1 s; sim6 -0.5 / -1.0 / -0.5 s; sim4 1.9 / 0.8 / -0.1 s. On this patient alone every model would fall under the floor; one patient decides nothing.

## 3. Computational environment

Confirmatory Stage 0 runs in one pinned environment: WSL2 Ubuntu, Python 3.12, torch 2.14.1 (CPU build), the package versions in `requirements.txt`, CPU only, 4 threads per job. Device, library versions and thread count all change floating-point summation order, so they change trained models slightly (on chb01 fold 0, 4 vs 8 threads gave test-score correlation 0.995; CPU vs DirectML GPU 0.94-0.99, against 0.84-0.90 between seeds). Within the pinned environment every job is bit-for-bit reproducible, and each job saves its trained FP32 weights, normalization and scores, so quantization and scoring can be re-run exactly without retraining.

The primary comparison is paired inside each job (quantized models built from that job's FP32 weights), so environment differences cannot bias it; they can only act like extra seed noise.

**Robustness check (secondary):** seed 0 for every patient is re-run on a second device (GPU), and the primary conclusion (each model inside or outside the null band, above or below the floor) is reported for both.
