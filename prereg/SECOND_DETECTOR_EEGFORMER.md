# Second detector family: EEGformer (assessment before any implementation or registration)

**Status:** working notes, 2026-11-24; updated 2026-11-25. Decided 2026-11-25: protocol option (b), the paper's pre-training then fine-tuning. Implemented (`src/eegformer.py`, `pipeline.pretrain`, `pipeline.run_eegformer_check`, tests) and drafted as update 8 (`prereg/OSF_UPDATE_8.md`); one workstation script runs everything (`scripts/run_eegformer_ws.sh`). Nothing registered or run beyond 2-epoch smoke tests.

## Why EEGformer

Aryal asked for a second detector family. Both detectors tested so far are small 1D CNNs (EpiDeNet, Ahlawat). EEGformer is a compact transformer (attention, LayerNorm, GELU, softmax), built for the same setting this study is about: low-channel wearable EEG on microcontrollers, with published CHB-MIT results and an MCU deployment. Its non-convolutional operations (softmax, LayerNorm, attention matmuls) quantize differently from convolutions, so it is a genuinely different test of the claim.

Sources:
- Busia et al., "Reducing False Alarms in Wearable Seizure Detection With EEGformer: A Compact Transformer Model for MCUs", IEEE TBioCAS 18(3):608-621, 2024, doi:10.1109/TBCAS.2024.3357509, CC BY 4.0 (open-access copy: cris.unibo.it handle 11585/1004688).
- Scrugli, Busia et al., EEGformer, BioCAS 2022 (iris.polito.it handle 11583/2978574).

## Code availability

**No public code found.** Neither paper links a repository or states that code is available, and web searches found none. The model was implemented in TensorFlow Keras by the authors. So this is a reimplementation from the paper, as EpiDeNet was. (Ahlawat, by contrast, had public code, which is why its fidelity check passed.)

## What the paper specifies (enough to build the model)

Table I of the 2024 paper gives the full topology:

| stage | layer | parameters |
|---|---|---|
| Embedding | Conv0 (1D) | input 4 x W, kernel K, stride K, output E channels |
| | Conv1 (1D) | kernel K, stride K, output E x S |
| | learned positional encoding | E x S |
| Encoder (1 block) | LayerNorm, Multi-Head Attention (H heads, q/k/v size d), LayerNorm, Dense0 (h, GELU), Dense1 (E, GELU), LayerNorm | residual connections around MHA and the feed-forward network |
| Classification | mean over the sequence, Dense2 | E -> 2 |

With W = 2048 (8 s at 256 Hz), K = 5, E = 32, S = 81, d = 32, H = 8, h = 128.

**Check (done):** a PyTorch reimplementation of Table I in the layer order given has **50,594 parameters against the paper's 50.6 K**, with S = 81 as stated. This is the analogue of the EpiDeNet MAC check (2,053,410 vs 2,053,516). It confirms the reading of Table I (q/k/v of size 32 per head, i.e. 3 x 8 x 32 projections). One misprint: Table I gives S' = 405 after Conv0, but a stride-5 convolution of 2048 samples gives 409; both lead to S = 81, so it changes nothing. The script is in the session scratchpad (`eegformer_count.py`) and would move into `src/eegformer.py` with a unit test.

Other stated details:
- Input: raw EEG, 4 temporal bipolar channels F7-T7, T7-P7, F8-T8, T8-P8, 256 Hz, 8 s windows. These are exactly this study's `temporal4` channel set.
- Training: two phases, subject-independent pre-training on the other patients (100 epochs), then subject-specific fine-tuning (50 epochs); Adam, learning rate 5e-5, batch size 16 (stated for the comparison CNNs, "trained with the two-step strategy evaluated for the EEGformer"; it is not stated separately for EEGformer). Training/validation windows non-overlapping; random 80/20 train/validation split.
- CHB-MIT protocol: patients chb01-chb08 only; leave one seizure record out; test windows 8 s with a 2 s hop; majority vote over 3 windows; false positives within 15 min after a seizure ignored; consecutive false positives counted as one event.
- CHB-MIT results (Table IV): 32/44 seizures detected (73%), segment sensitivity 65.5%, 0.15 FP/h (event level), median 0 FP/h over 40 test records, average latency 15.2 s.
- MCU deployment: 8-bit integer inference (integer Softmax, LayerNorm and GELU) on Apollo4, GAP9 and another RISC-V platform. So INT8 deployment is what the authors did; this study's question applies directly.

## What the paper does not specify (a reimplementation must choose)

- Input filtering and normalization (raw signal; scaling not stated).
- Loss on CHB-MIT (a weighted loss is stated only for their private dataset), dropout, weight decay, early stopping.
- How the pre-training pool was built for chb01-08 (all of each other patient's records, or seizure records only; the private-dataset section says seizure records only).
- The threshold (default argmax implied by majority voting).
- Pre-norm vs post-norm placement is implied by Table I's order but not stated in words.

These are the same kind of gaps that sank the EpiDeNet reimplementation (its gate failed on false positives). The fidelity risk is real.

## Proposed design for update 8 **[decide]**

1. **Model:** EEGformer as Table I, PyTorch, `temporal4` channels, 8 s windows.
2. **Protocol [decide]:**
   - (a) This study's registered patient-specific design (the CHB-MIT confirmatory design, all 24 patients, seeds 0-4), with EEGformer trained subject-specifically only. Comparable with the Ahlawat test, but not EEGformer's published protocol, so its published numbers cannot be the fidelity target.
   - (b) Add EEGformer's two-phase pre-training + fine-tuning inside the same folds (pre-train on the other patients, never on the test patient). Closer to the paper, more code (a pre-training stage per patient, ~24 x 5 extra trainings), and a stronger fidelity check.
   Recommendation: (b), because a second detector that fails its own fidelity check would add nothing (as Siena showed).
3. **Fidelity check:** (A) architecture check as above (done: parameter count); (B) operating point, as registered for Ahlawat (FP32 pooled test specificity within 0.995 +/- 0.005 for two thirds of patient-seeds); optionally (C) a protocol-matched check on chb01-08 against Table IV (32/44 seizures, 0.15 FP/h), with tolerances fixed in advance.
4. **Quantization:** ONNX Runtime static INT8 as for the other models; check which transformer operators ORT quantizes (MatMul, Gemm, Conv yes; LayerNorm, Softmax and GELU may stay in float). If they stay float, that must be stated, because the authors' MCU runs them in integer. Simulated 8/6/4-bit and QAT need extending to the attention matmuls and activations.
5. **Decision rule:** unchanged (H1 supported if pooled INT8 excess latency is above the FP32 seed band and at least 2 s).

## Effort and timeline

- Model, unit tests, ONNX export and INT8 check: about 2-3 days.
- Simulated low-bit and QAT for attention layers: about 2-3 days.
- Pre-training stage (option b): about 2 days.
- Draft update 8, Aryal review, submit: before or at the Dec 15 meeting.
- Workstation run: 690 jobs; EEGformer is about 50 K parameters and 14.7 MOPs per window, so per-job time should be similar to or below Ahlawat's (~11 min/job, 47.7 h total), plus pre-training under option (b). Not measured yet.

Fits the plan: implement in early December, register mid-December, run over the holidays, analyse in January. Not needed for the Brown abstract.
