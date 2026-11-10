# OSF registration update 2 (draft): confirmatory test with Ahlawat's model

Draft, not submitted. Register before any Ahlawat job is run in this pipeline. Bracketed items are open decisions (listed at the end) to settle with the advisor first. Same mechanics as update 1 (`prereg/OSF_UPDATE_FORM.md`): append each paragraph to the end of its field; files cannot be added, so cite the commit.

## Justification tab

> Second update. Under the rule registered in update 1 (2026-11-10), the protocol-matched reimplementation check of EpiDeNet failed (seizures detected 95.1%, pass; voted window false positives per hour 15.56, outside 1.12-4.48), and a recheck of the architecture against EpiDeNet's Table I found no discrepancy (every layer matches; 2,053,410 vs 2,053,516 MACs). As registered, Ahlawat's model therefore becomes the primary model. This update registers the confirmatory test of H1 with that model, its fidelity check, seeds and compute, before any of its jobs are run in this pipeline. One Ahlawat job (chb01, fold 0, seed 0) was run during pipeline development in October 2026 to test the code path and the threshold-tie fix; its scores were seen during debugging and it is not part of the confirmatory run. Two exploratory analyses were run after update 1 and before this update, and are disclosed here: the reimplementation check repeated with unweighted cross-entropy, and W4A8 and FP16 versions of Stage 0's EpiDeNet models built from their saved weights.

## Page 2: Hypotheses (add at the end)

> Update 2. H1, H2 and H3 are unchanged. Their confirmatory test (H1's INT8 test only) is now run with Ahlawat's model (Ahlawat 2026, public code final.py, class EEGCNN) as described under Inference criteria; the Stage 0 EpiDeNet results are exploratory (update 1).

## Page 5: Variables → Manipulated variables (add at the end)

> Update 2. The model is Ahlawat's 1D CNN: 18 bipolar channels (his montage), 8 s windows at 128 Hz, his training settings (Adam, learning rate 1e-4, batch 256, at most 200 epochs, early stopping after 20 epochs), trained and evaluated with this study's splits, thresholds and scoring. Two differences from his code, fixed in advance: two output logits with softmax instead of one logit with a sigmoid (same network otherwise), and this study's preprocessing (causal 0.5-40 Hz band-pass, decimation to 128 Hz, standardization from training windows) instead of his per-record z-score. Precisions as registered: FP32, post-training INT8 (ONNX Runtime, primary), simulated 8-, 6- and 4-bit, quantization-aware 8-bit; [W4A8 and FP16 added as exploratory]. Simulated sub-8-bit models are stress points, not deployment scenarios (update 1).

## Page 6: Analysis Plan → Inference criteria (add at the end)

> Update 2: confirmatory test with Ahlawat's model.
>
> Design: patient-specific, as registered (each patient's records grouped into folds; fold k tests on fold k, validates on fold k+1, trains on the rest). All 24 CHB-MIT cases qualify with the 18-channel montage: 683 usable records, 138 seizure records, 138 folds. Seeds: [3 (0, 1, 2), as in Stage 0 | 5 (0-4)]. Thread count, environment and code fixed at commit [hash] (CPU, 4 threads per job, [local WSL environment | cluster environment, recorded per job]).
>
> Fidelity check (decided before the primary test; Ahlawat's published numbers are window AUROC on a split that leaks windows across train and test, so they cannot serve as an event-level reference): [Option A, implementation: before the run, Ahlawat's own final.py, run unchanged on his split, gives FP32 test AUROC within 0.005 of his reported 0.9617 (already done: 0.9618), and this pipeline's AhlawatCNN has the same layers and parameter count as his EEGCNN apart from the output layer; check by script, reported. | Option B, operating point: as A, plus after the run, pooled FP32 test window specificity within 0.995 +/- 0.005 for at least two thirds of patient-seed values; if it fails, the results are reported as exploratory.]
>
> Primary test and decision: as registered for Stage 0, applied to Ahlawat's model. Pooled excess latency of post-training INT8 against the FP32 seed-noise null (95% band from all ordered FP32 seed pairs); patient-bootstrap intervals and the mixed-effects model as registered. H1 is supported if the pooled INT8 excess latency lies above the null band and is at least 2 s; it is not supported if it lies inside the band or below 2 s. The stop rule's wording carries over: if INT8 is not supported but 6-bit or 4-bit is, the paper reports where compression starts to cost latency.
>
> Reporting: whatever the outcome, the paper reports the Stage 0 EpiDeNet results (exploratory), both failed EpiDeNet checks and the Table I recheck alongside this test.

## Page 6: Analysis Plan → Exploratory analysis (add at the end)

> Update 2. Exploratory with Ahlawat's model: every registered exploratory analysis; the recall-at-false-alarm-cap analysis of update 1 (caps 0.5, 1 and 2 per 24 h); [W4A8 and FP16 built from the saved FP32 weights, scored like the other post-training models]. Exploratory with EpiDeNet, run after update 1 and before update 2: (1) the protocol-matched reimplementation check repeated with unweighted cross-entropy (default decision; same folds, seeds and early stopping), to test whether class weighting explains the check's failure; it cannot change any registered decision; (2) W4A8 (4-bit weights, 8-bit activations) and FP16 versions of all 414 Stage 0 models, built from their saved FP32 weights without retraining, with excess latency and recall at the caps.

## Page 7: Other (add at the end)

> Update 2: code at commit [hash] (scripts/run_patient.py --model ahlawat; scripts/analyze_frontier.py; scripts/analyze_stats.py). Compute: about 56 minutes per Ahlawat job on the development machine (chb01, fold 0), so [414 | 690] jobs need about [8 | 13] days at two parallel jobs locally, or [a capped cluster allocation].

---

## Open decisions (settle before submitting)

1. **Seeds: 3 or 5.** 3 matches Stage 0 and halves compute (about 8 days locally). 5 was the plan's Stage 1 and narrows the seed null band. Recommendation: 3 for the undergraduate venue's timeline; register 5 only if the cluster allocation comes through before the run starts.
2. **Where it runs.** Locally it ties up the laptop for about 8 days (3 seeds). The cluster needs Aryal's capped pilot allocation; Stage 0's floating-point results depend on the environment, so the environment must be fixed in the registration and not mixed within the run.
3. **Fidelity check: A or B.** A only checks the implementation against Ahlawat's code (already passes). B adds an operating-point check after the run, which can fail. Recommendation: B. It is a real check, and its failure mode (results exploratory) is honest. But it means a second failed check is possible.
4. **Include W4A8 and FP16 for Ahlawat.** Cheap (no training); decide after seeing whether they say anything new on EpiDeNet, which is allowed because they are exploratory either way.
5. **H1 decision wording.** The original registration states the stop rule but not a "supported" criterion for H1 in so many words; the draft makes it explicit using the same band and 2 s floor. Check this wording reads as a clarification, not a change.
6. **Timing.** About 8 days of compute means starting by about Dec 1 to have results before the Dec 15 meeting; the abstract (Jan 10) can cite them only if the run finishes by early January.
