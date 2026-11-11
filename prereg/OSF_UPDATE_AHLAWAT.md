# OSF registration update 2 (draft): confirmatory test with Ahlawat's model

Draft, not submitted. Register before any Ahlawat job is run in this pipeline. Decisions taken 2026-11-10: 5 seeds for the confirmatory test, with a pre-specified interim report on seeds 0-2 for the undergraduate conference; run on the laptop (WSL); fidelity check B; W4A8 and FP16 included as exploratory. Same mechanics as update 1 (`prereg/OSF_UPDATE_FORM.md`): append each paragraph to the end of its field; files cannot be added, so cite the commit. Fill `[commit]` with the commit that contains this file and `scripts/check_ahlawat.py`.

## Justification tab

> Second update. Under the rule registered in update 1 (2026-11-10), the protocol-matched reimplementation check of EpiDeNet failed (seizures detected 95.1%, pass; voted window false positives per hour 15.56, outside 1.12-4.48), and a recheck of the architecture against EpiDeNet's Table I found no discrepancy (every layer matches; 2,053,410 vs 2,053,516 MACs). As registered, Ahlawat's model therefore becomes the primary model. This update registers the confirmatory test of H1 with that model, its fidelity check, seeds, an interim report and compute, before any of its jobs are run in this pipeline. One Ahlawat job (chb01, fold 0, seed 0) was run during pipeline development in October 2026 to test the code path and the threshold-tie fix; its scores were seen during debugging, and it is rerun from scratch as part of the confirmatory run like every other job. Two exploratory analyses were run after update 1 and before this update, and are disclosed here: the reimplementation check repeated with unweighted cross-entropy, and W4A8 and FP16 versions of Stage 0's EpiDeNet models built from their saved weights.

## Page 2: Hypotheses (add at the end)

> Update 2. H1, H2 and H3 are unchanged. Their confirmatory test (H1's INT8 test only) is now run with Ahlawat's model (Ahlawat 2026, public code final.py, class EEGCNN) as described under Inference criteria; the Stage 0 EpiDeNet results are exploratory (update 1).

## Page 5: Variables → Manipulated variables (add at the end)

> Update 2. The model is Ahlawat's 1D CNN: 18 bipolar channels (his montage), 8 s windows at 128 Hz, his training settings (Adam, learning rate 1e-4, batch 256, at most 200 epochs, early stopping after 20 epochs), trained and evaluated with this study's splits, thresholds and scoring. Two differences from his code, fixed in advance: two output logits with softmax instead of one logit with a sigmoid (same network otherwise), and this study's preprocessing (causal 0.5-40 Hz band-pass, decimation to 128 Hz, standardization from training windows) instead of his per-record z-score. Precisions as registered: FP32, post-training INT8 (ONNX Runtime, primary), simulated 8-, 6- and 4-bit, quantization-aware 8-bit; added as exploratory: W4A8 (4-bit weights, 8-bit activations) and FP16, built from each job's saved FP32 weights. Simulated sub-8-bit models are stress points, not deployment scenarios (update 1).

## Page 6: Analysis Plan → Inference criteria (add at the end)

> Update 2: confirmatory test with Ahlawat's model.
>
> Design: patient-specific, as registered (each patient's records grouped into folds; fold k tests on fold k, validates on fold k+1, trains on the rest). All 24 CHB-MIT cases qualify with the 18-channel montage: 683 usable records, 138 seizure records, 138 folds. Seeds 0-4 (690 jobs), run in two batches with identical code and environment: seeds 0-2 first, then seeds 3-4. Environment fixed for the whole run: WSL2 Ubuntu, Python 3.12, torch 2.14.1 CPU build, the versions in requirements.txt, CPU only, 4 threads per job, code at commit [commit].
>
> Interim report (seeds 0-2, pre-specified): when seeds 0-2 finish, the registered analyses are computed on them and may be reported, labelled interim, in a conference abstract or poster. The interim report makes no decision: it cannot stop the run, change the design, or replace the confirmatory test, and seeds 3-4 are run whatever it shows.
>
> Fidelity check (decided before the primary test; Ahlawat's published numbers are window AUROC on a split that leaks windows across train and test, so they cannot serve as an event-level reference). Both parts must pass. (A) Implementation, checked before the run: Ahlawat's own final.py, run unchanged on his split, reproduces his reported FP32 test AUROC within 0.005 (done: 0.9618 vs 0.9617), and scripts/check_ahlawat.py shows this pipeline's model has his EEGCNN's layers and shapes apart from the registered output layer, giving the same seizure probability as his model with his weights (done: passed, difference 0). (B) Operating point, checked on seeds 0-4 after the run: per patient and seed, FP32 test window specificity pooled over all held-out hours within 0.995 +/- 0.005 (the registered specificity check) for at least two thirds of patient-seed values. If either part fails, the confirmatory test is reported as exploratory and the failure is reported with it.
>
> Primary test and decision (seeds 0-4): as registered for Stage 0, applied to Ahlawat's model. Pooled excess latency of post-training INT8 against the FP32 seed-noise null (95% band from all ordered pairs of FP32 seeds within a patient); patient-bootstrap intervals and the mixed-effects model as registered. H1 is supported if the pooled INT8 excess latency lies above the null band and is at least 2 s; it is not supported if it lies inside the band or below 2 s. The stop rule's wording carries over: if INT8 is not supported but 6-bit or 4-bit is, the paper reports where compression starts to cost latency.
>
> Reporting: whatever the outcome, the paper reports the Stage 0 EpiDeNet results (exploratory), both failed EpiDeNet checks and the Table I recheck alongside this test.

## Page 6: Analysis Plan → Exploratory analysis (add at the end)

> Update 2. Exploratory with Ahlawat's model: every registered exploratory analysis; the recall-at-false-alarm-cap analysis of update 1 (caps 0.5, 1 and 2 per 24 h); W4A8 and FP16, built from the saved FP32 weights and scored like the other post-training models. Exploratory with EpiDeNet, run after update 1 and before update 2: (1) the protocol-matched reimplementation check repeated with unweighted cross-entropy (default decision; same folds, seeds and early stopping), to test whether class weighting explains the check's failure; it cannot change any registered decision; (2) W4A8 and FP16 versions of all 414 Stage 0 models, built from their saved FP32 weights without retraining, with excess latency and recall at the caps.

## Page 7: Other (add at the end)

> Update 2: code at commit [commit] (scripts/run_patient.py --model ahlawat --seeds 0 1 2, then --seeds 3 4; scripts/check_ahlawat.py; scripts/rescore_bitwidths.py; scripts/analyze_frontier.py; scripts/analyze_stats.py). Compute: about 56 minutes per Ahlawat job on the development machine (chb01, fold 0), so seeds 0-2 (414 jobs) take about 8 days and seeds 3-4 (276 jobs) about 5 more at two parallel jobs.

---

## Before submitting

1. **H1 wording.** The original registration states the stop rule but not a "supported" criterion for H1 in so many words; this draft makes it explicit with the same band and 2 s floor. Ask Aryal whether it reads as a clarification, not a change.
2. **Commit.** Commit and push this file and `scripts/check_ahlawat.py`, then put that commit's hash in the two `[commit]` places.
3. **Rescore support for Ahlawat.** Done: the rebuild-and-rescore test now runs for both models on synthetic data (`test_rescore_fold_rebuilds_a_finished_job_exactly[ahlawat]`), so no real Ahlawat job is needed before registration. Point `rescore_bitwidths.py --runs` at the Ahlawat run folder afterwards.
4. **Start.** Submit, then start seeds 0-2 once the laptop is free (the EpiDeNet runs finish about Nov 11). Seeds 0-2 finish about 8 days later; seeds 3-4 about 5 days after that.
