# Systematic literature review: protocol and search log

*Started 2026-11-24 for the MLHC submission. Replaces the narrative `audit/AUDIT.md` as the basis for the Related Work section. Follows PRISMA 2020 for reporting (flow diagram, search strings, dates, counts). Not registered (PROSPERO does not take methods reviews); the protocol is fixed here before screening, and changes are logged at the bottom.*

## Question

How have studies evaluated the effect of compressing (quantizing, pruning, or otherwise reducing precision of) EEG seizure-detection models for low-power hardware, and do any of them evaluate the compressed model at the event level, where false-alarm rate and detection latency trade off, rather than by window-level accuracy?

## Eligibility

Include studies that:
1. detect (not predict or classify interictal activity) epileptic seizures from scalp or intracranial EEG;
2. use a learned model (neural network, tree ensemble, SVM or similar);
3. compress or reduce the precision of that model for deployment (post-training quantization, quantization-aware training, fixed-point, binarization, pruning, knowledge distillation to a smaller model), or deploy it on a microcontroller, ASIC, FPGA or neuromorphic chip with reduced precision;
4. report detection performance of the deployed or compressed model.

Exclude: seizure prediction only; non-EEG modalities only (accelerometry, ECG, EMG) unless combined with EEG; feature-extraction hardware without a learned classifier; non-English; conference abstracts without results. Studies of compression in other biosignal tasks are noted as context, not included.

## Sources and search strings

| source | string | status |
|---|---|---|
| PubMed | Q1: `(seizure detection) AND (quantization OR quantized OR "fixed-point" OR "8-bit" OR pruning OR "model compression")` | run 2026-11-24: 34 records |
| PubMed | Q2: `(seizure detection) AND (microcontroller OR "edge computing" OR "low-power" OR "on-device") AND (neural network OR deep learning)` | run 2026-11-24: 32 records |
| IEEE Xplore | same concepts, adapted to its syntax (seizure AND detection) AND (quantiz* OR "fixed-point" OR int8 OR "8-bit" OR pruning OR compression OR microcontroller OR MCU OR "edge") | **to run** (manual; most of this literature is in IEEE venues: TBioCAS, BioCAS, ISCAS, EMBC, JSSC) |
| ACM Digital Library | same | **to run** |
| arXiv (eess.SP, cs.LG) | same | **to run** |
| Google Scholar | forward citations of EpiDeNet, EEGformer, Ahlawat, SzCORE; backward snowballing from included studies | **to run** |

PubMed is not where most of this literature sits, so the PubMed results below are a floor, not the review.

## Data extraction (per included study)

Model and size; dataset(s) and protocol (patient-specific or cross-patient); compression method and bit-widths; whether the compressed model is compared with its full-precision version on the same folds; metrics reported for the compressed model (window accuracy / sensitivity / specificity / AUROC; event sensitivity; false alarms per hour or 24 h; detection latency); whether thresholds are re-tuned after compression; hardware and energy; code availability.

The key extracted variable: **does the study report event-level false alarms and latency for the compressed model against full precision, at a matched operating point?** The study's claim of novelty rests on this being rare or absent.

## Search log and screening so far

PubMed, 2026-11-24: 66 records, 60 unique (`paper/lit_review/pubmed_2026-11-24.csv`, with automatic keyword flags for screening aid only: EEG, learned model, compression, comparison with floating point, event-level metrics). Title/abstract screening by one reviewer (to be checked by a second reader for a subsample):

- **Clearly irrelevant (about 20):** neuroscience or pharmacology papers caught by "pruning" or "quantization" (e.g. synaptic pruning, LC assay), seizure-prediction-only, HFO detection, control theory.
- **For full-text screening (11):**
  - 34181550 (2021) RISC-V CNN coprocessor for real-time epilepsy detection, wearable: compares quantized and float, mentions event metrics.
  - 33794507 (2021) Edge deep learning for neural implants, seizure detection and prediction.
  - 39137083 (2025) RVDLAHA, RISC-V DLA for on-device seizure detection: compares with float.
  - 40354815 (2025) Memory-optimized random forest for implantable seizure detection: compares with float, mentions event metrics.
  - 34201480 (2021) Seizure detection on an ultra-low-power RISC-V processor using a CNN.
  - 36417737 (2023) LightSeizureNet.
  - 38261487 (2024) EEGformer (Busia et al.), INT8 on MCUs.
  - 35737626 (2022) Memristive CNNs for seizure detection and prediction.
  - 33011647 (2020) Seizure detection on compressively-sensed EEG, ultra-low-power.
  - 30440858 (2018) Hardware implementation of an energy-optimized CNN for seizure detection.
  - 40586847 (2025) EEG preprocessing parameters and ultra-low-power seizure detection.
- **Uncertain, to recheck:** neuromorphic/spiking detectors (39413626, 40335613, 38268711, 35110665) and tree-based on-chip classifiers (40030347, 39412966, 32746347): low precision by design rather than compression of a float model; decide whether they meet criterion 3.

Preliminary observation (to be confirmed by full-text screening, not to be cited yet): only 3 of 60 PubMed records mention a comparison with floating point at all, and most report window-level accuracy or sensitivity.

## Timeline

- Dec 1-12: IEEE Xplore, ACM, arXiv searches; title/abstract screening; full-text screening of PubMed candidates.
- Dec 13-31: snowballing; extraction table; PRISMA flow diagram.
- January: Related Work section drafted from the extraction table.

## Changes to this protocol

(none yet)
