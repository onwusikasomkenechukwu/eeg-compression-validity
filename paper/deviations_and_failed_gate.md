# Draft paper text: deviations from the pre-registration and the failed sanity gate

*For the Methods ("Pre-registration and deviations") and Results ("Reimplementation check") sections. Bracketed items depend on decisions still open.*

## Pre-registration and deviations

The claim, hypotheses, primary test, stop rule, FP32 sanity gate, latency definition, split rule and analysis plan were registered on OSF before the confirmatory run [OSF link, registered 2026-10-25; analysis code at commit 3a9b77d]. One patient (chb01) was analyzed beforehand as a pipeline pilot; the decisions made after it (an interpolated primary endpoint, a per-patient specificity check, a 300-epoch cap, latency from raw alarms, and a strict threshold comparison) are listed in the registration. The confirmatory run was paused once and resumed without changes; two interrupted jobs were discarded and rerun from scratch. [Any registration update and its date.]

## Reimplementation check (FP32 sanity gate)

The registered gate compared the FP32 reimplementation with EpiDeNet's published CHB-MIT results in EpiDeNet's own units. It required seizures detected of at least 82.3% of usable seizures (EpiDeNet's 8.8% miss rate, doubled) and voted window false positives per hour within a factor of two of EpiDeNet's 2.24 (1.12-4.48). The reimplementation detected 92.6% of seizures (171-172 of 185 across seeds; EpiDeNet 91.2%) but produced 5.83 voted false-positive windows per hour, so **the gate failed**. As registered, this indicates that the reimplementation does not reproduce EpiDeNet, not that the hypothesis is false.

A post hoc investigation (not registered) found no systematic bias in how thresholds transfer from validation to test: median test specificity equals the 0.995 target. False positives were concentrated in a few long seizure-free recordings with sustained high-amplitude non-seizure activity: 1% of test recordings carried 57% of false-positive windows. At a threshold that reproduces EpiDeNet's specificity, the reimplementation detects 80.4% of seizures against EpiDeNet's 91.2%. The reimplementation is therefore weaker than the published model at matched specificity. Likely contributors are the loss (class-weighted cross-entropy rather than EpiDeNet's SSWCE), the assumed temporal channels and filtering, and less training data per fold than EpiDeNet's leave-one-seizure-record-out design.

## Consequences for the claims

[Depends on the decision below. If no rerun: the primary comparison is paired within each trained model and thresholded identically for FP32 and its quantized versions, so a weaker FP32 baseline does not bias the FP32-vs-INT8 contrast, but the results describe a detector that underperforms EpiDeNet and are reported as exploratory. If a registered rerun or replication follows: report it as the confirmatory result and Stage 0 as the failed first attempt.]
