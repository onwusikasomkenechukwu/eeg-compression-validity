# Table I recheck after the failed reimplementation check

The protocol-matched check failed (`sanity_gate.md`: detection 95.1%, pass; voted window FP/h 15.56, outside 1.12-4.48). This is the step the registered rule calls for next: "Table I is rechecked against the code, and if still off, Ahlawat's model becomes primary for later stages."

## Table I vs `src/epidenet.py`

Read from the paper's text (Ingolfsson et al. 2023, arXiv 2309.07135, Table I) and compared layer by layer:

| block | paper: filters, kernel, pool, output | code | match |
|---|---|---|---|
| phi1 | 4, (1,4), MaxPool (1,8), (4,C,T//8) | 4, (1,4), MaxPool (1,8) | yes |
| phi2 | 16, (1,16), MaxPool (1,4), (16,C,T//32) | 16, (1,16), MaxPool (1,4) | yes |
| phi3 | 16, (1,8), MaxPool (1,4), (16,C,T//128) | 16, (1,8), MaxPool (1,4) | yes |
| phi4 | 16, (16,1), MaxPool (4,1), (16,C//4,T//128) | 16, (16,1), MaxPool (4,1) | yes |
| phi5 | 16, (8,1), (16,C//4,T//128) | 16, (8,1) | yes |
| pool | AdaptiveAveragePool, (16,1,1) | AdaptiveAvgPool2d(1) | yes |
| phi6 | Dense 2 | Linear(16, 2) | yes |

Operation count (`scripts/check_epidenet.py`, input 4 x 2048 as in Table IV): 2,053,410 MACs vs the paper's 2,053,516 (difference 106, 0.005%). Input: 4 temporal channels, 4 s windows of 1024 samples at 256 Hz, as stated in Section II-F.

The choices the paper leaves open stay as documented in `src/epidenet.py` ("same" padding, BatchNorm + ReLU after each convolution, block 5's kernel read as (8,1)); none changes the MAC count, and the table does not decide them.

**Result: no discrepancy between Table I and the code. Nothing to correct, so the check's result stands: still off.**

## Decision under the registered rule

The reimplementation does not reproduce EpiDeNet's CHB-MIT numbers. Per the rule registered before the check ran, Ahlawat's model becomes the primary model for later stages. The failed registered gate, the investigation, the failed protocol-matched check and this recheck are all reported.

## Descriptive context (not part of the rule)

Window-level FP32 metrics, mean over the 414 jobs (Table II's values in brackets: raw, then with the 3-window vote):

| | ours, raw | ours, voted | EpiDeNet, raw | EpiDeNet, voted |
|---|---|---|---|---|
| sensitivity (%) | 81.89 | 76.02 | 68.56 | 68.73 |
| specificity (%) | 98.33 | 98.70 | 99.52 | 99.75 |
| FP/h (hours-weighted) | 18.37 | 15.56 | 4.29 | 2.24 |
| seizures detected | | 95.1% of 185 | | 165/181 (91.2%) |

The reimplementation sits at a more sensitive, less specific operating point than the paper's: more windows and seizures detected, more false positives. One plausible reason lies outside Table I: training uses cross-entropy weighted by inverse class frequency (`pipeline.fit`), so the default decision (p > 0.5) leans toward the seizure class. The paper does not state its CHB-MIT loss or class handling; Table II has no SSWCE column, which suggests plain cross-entropy. Other unstated differences: optimizer and learning rate, filtering, normalization, which 181 seizures were counted (185 usable here), and 5 seeds in the paper vs 3 here. False positives are concentrated: chb04 gives 43% of them, and three jobs (chb04 fold 0, seeds 1 and 2; chb06 fold 1, seed 1) give over half; the median patient is at 5.56 FP/h.

Testing the class-weighting explanation (for example, retraining with unweighted cross-entropy) would be a new post hoc analysis. It cannot change the registered decision above; if run, it would be reported as exploratory, and using it to keep EpiDeNet as primary would need a new registered update first.
