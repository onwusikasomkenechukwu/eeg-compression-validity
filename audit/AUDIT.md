# Audit: how compressed seizure detectors are certified (2018-2026)

Question from the research plan: for papers that compress a seizure detector, which metric certifies the compressed model, are event-level false alarms reported for the compressed model, and is detection latency reported at all? Added column: does the paper's "FP/h" count misclassified windows or alarms?

Search (Oct 25, 2026): web and arXiv searches on quantized / binarized / pruned / distilled / fixed-point / INT8 / TinyML / FPGA / ASIC seizure detectors, plus the reference lists of the plan's papers. Every row below was checked against the paper's full text, except where marked. Not a systematic review: no database export or screening protocol, so the count is a lower bound on the literature, not a census.

## Main table: papers that compress a seizure detector (n = 14)

| # | Paper | Compression | Data | Metric certifying the compressed model | Event-level false alarms for the compressed model? | Latency reported? | "FP/h" counts |
|---|---|---|---|---|---|---|---|
| 1 | Liu et al. 2021, *J. Neural Eng.* (arXiv 2012.00307), edge DL for neural implants | 8-bit fixed point (vs 16-bit), model compression | CHB-MIT | Segment accuracy, before vs after (< 0.5% drop) | **Yes, compressed model only** (Table 2); no unquantized comparison | No (a hit within 5 s of onset counts; no latency values) | Events (sliding-window majority vote) |
| 2 | *Epileptic seizure detection on an ultra-low-power embedded RISC-V processor using a CNN*, *Biosensors* 2021 (PMC8301882) | 16-bit fixed point (Q1.14) on GAP8 | CHB-MIT | Sensitivity only for the deployed model (85%) | No (fp/h for the float model only) | No (per-window run time only) | **Windows** (1 s sequences per hour) |
| 3 | Busia et al. 2022, BioCAS (EEGformer) | 8-bit, quantization-aware fine-tuning | CHB-MIT | Not reported separately for the quantized model | Not stated (FP/h reported without saying which model) | Yes (onset latency 15 s), model not stated | Not stated |
| 4 | Li et al. 2022, *IEEE TBioCAS* (arXiv 2206.09951), memristive CNN | Quantization-aware training for low-resolution crossbars | Bonn (detection) | Accuracy | No | No | n/a |
| 5 | Zheng et al. 2023 (arXiv 2304.06038), knowledge-distilled GNN | Knowledge distillation + channel reduction | TUSZ | F1, AUROC | No | No | n/a |
| 6 | Ingolfsson et al. 2023 (arXiv 2309.07135), EpiDeNet | INT8 on Cortex-M4F/M7, GAP8, GAP9 | CHB-MIT, PEDESITE | Sensitivity / specificity (about +/-0.1%) | No (FP/h for FP32 only) | No | **Windows** (4 s; (1 - specificity) x 900) |
| 7 | Saidi et al. 2023, *IJ-ICT* 12(3), FPGA epilepsy detection | INT8 (Xilinx DNNDK) + pruning | CHB-MIT | Toolkit's "without a loss in accuracy" | No | No | n/a |
| 8 | Busia et al. 2024, *IEEE TBCAS* 18(3), EEGformer for MCUs | INT8 (Quantlab) | CHB-MIT, PEDESITE | "no accuracy drop (not shown)" | No (0.15 FP/h not tied to the quantized model) | Yes (onset latency), not for the quantized model | Not stated |
| 9 | Reisinger et al. 2025, *Epilepsia* 66(10) | INT8 (TFLite) | 145 patients (scalp, focal) | Event sensitivity, false detections/h, detection delay, all **on the quantized model only** | **Yes, compressed model only**; no FP32 comparison | Yes, quantized model only | Events |
| 10 | Harshit & Mounvik 2025 (arXiv 2509.05190) | Structured pruning (50% of kernels) | Segment dataset | Accuracy, macro-F1 | No | No | n/a |
| 11 | Hizem et al. 2025, *Biomed. Eng. Comput. Biol.* 16 | INT8 (TFLite) + pruning | Bonn (segments) | Accuracy "remained almost unchanged" (no numbers) | No | No | n/a |
| 12 | Shayestehroodi et al. 2026 (arXiv 2606.12742) | 8/16-bit, LQ-Net low-bit and binarized | TUSZ | AUROC, AUPRC, F1, TNR | No | No | n/a |
| 13 | Tegon et al. 2026 (arXiv 2603.26716), FEMBA on the edge* | QAT to 2-bit weights, W8A8 | TUAB, TUAR, TUSL | AUROC / accuracy | No | No (inference time only) | n/a |
| 14 | Ahlawat 2026 (arXiv 2607.16296) | INT8 PTQ and QAT, channel pruning, 2:4 sparsity | CHB-MIT | Window AUROC (verified by re-running his code) | No | No | n/a |

\* FEMBA is an EEG foundation model; its seizure task is one class of TUSL's multiclass labels. Kept because it certifies a compressed seizure-capable EEG detector, flagged as borderline.

## Summary (k of n, n = 14)

- **Before-vs-after comparison of event-level false alarms or latency: 0 of 14.** No paper reports either quantity for both the uncompressed and the compressed model. The scope-kill condition in the plan is not met.
- **Event-level false alarms reported for the compressed model at all: 2 of 14** (Liu 2021, Reisinger 2025), both for the compressed model only. Two more (Busia 2022, 2024) report FP/h without saying which model it describes.
- **Detection latency reported at all: 3 of 14** (Busia 2022, Busia 2024, Reisinger 2025); for a compressed model with no FP32 counterpart: 1 (Reisinger).
- **Compressed model certified by window- or segment-level metrics, or by an unquantified claim: 12 of 14** ("no loss", "almost unchanged", "not shown" in 4 of them).
- **"FP/h" definition:** among the 6 papers that report an hourly false-positive figure, 2 count misclassified windows (EpiDeNet, the RISC-V/GAP8 paper), 2 count events (Liu, Reisinger), and 2 do not say (both EEGformer papers).

One sentence for the paper: *Of 14 papers that compress a seizure detector, none compares event-level false alarms or detection latency before and after compression; 12 certify the compressed model with window-level metrics or an unquantified claim of no loss.*

## Checked and excluded

| Paper | Reason |
|---|---|
| Ingolfsson et al. 2021, BioCAS (arXiv 2106.08008) | Tree-based classifiers; no neural-network compression |
| Hügle et al. 2018 (arXiv 1806.04549) | CNN on an implantable MCU, not compressed (quantization named as future work); reports latency and false detections for its uncompressed model |
| Ingolfsson et al. 2024, *IEEE TBCAS* (BrainFuseNet) | GAP9 deployment with no compression described |
| Samakovlis et al. 2024 (arXiv 2406.03886), BiomedBench | Hardware benchmark; no detection accuracy reported |
| Zhao et al. 2022 (arXiv 2206.07518), binary 1D CNN | Seizure **prediction**, not detection (AUC, sensitivity, false prediction rate) |
| Zhao, Yang & Sawan 2022, *IEEE TBME* 69(1) | Seizure **prediction** at several quantization levels (cited by Reisinger 2025 as showing loss only below 8 bits); not verified from full text |

## Not verified from the full text (not counted)

- Truong et al. 2018, *IEEE JETCAS*, "Integer convolutional neural network for seizure detection" (paywalled; abstract reports no event metrics).
- Muneeb (York University thesis), 1-bit spiking CNN on STM32H747: false-positive rate 0.69/h reported for the initial, unquantized validation only.
- TU Delft MSc thesis 2021, quantized networks on FPGA (TUSZ): sensitivity and MCC.

## Limits

- 14 papers, below the plan's 15-25 target; the three unverified items above would bring it to 17. A systematic search (Scopus / IEEE Xplore export with a screening log) would make the count defensible as a census.
- Two rows (Busia 2022, 2024) are scored conservatively as "not for the compressed model" because the papers do not say which model their event metrics describe.
