# EEG Compression Validity

Does post-training quantization move a seizure detector along the false-alarm / latency trade-off that its window-level metrics cannot see? Pre-registration draft: `prereg/PREREGISTRATION_DRAFT.md`.

## Layout

| Path | What |
|---|---|
| `src/records.py` | Shared: 256 Hz, causal 0.5-40 Hz filter and decimation, versioned float16 cache (memory-mapped), window labels, patient-specific and cross-patient fold designs |
| `src/chbmit.py` | CHB-MIT: temporal-4 and Ahlawat's 18 bipolar channels; patient groups (chb01 + chb21) |
| `src/siena.py` | Siena: temporal-4 bipolar channels derived from referential T3/T4/T5/T6, 512 -> 256 Hz; validated seizure-list parser with documented corrections |
| `src/seizeit2.py` | SeizeIT2 (BIDS): the subject's main two-channel behind-the-ear montage; seizures from `*_events.tsv` |
| `src/epidenet.py` | EpiDeNet from its Table I (checked against the paper's MAC count; channel pooling adapts below 4 channels) |
| `src/models.py` | Model specs: EpiDeNet (primary) and Ahlawat's 1D CNN (secondary) with their windows, rates and training settings |
| `src/quantize.py` | ONNX Runtime static INT8 (primary), simulated 8/6/4-bit (dose-response), quantization-aware 8-bit training |
| `src/pipeline.py` | One fold, any dataset / model / arm: train FP32, quantize, threshold, smooth, score with SzCORE, latency |
| `src/scoring.py` | SzCORE event scoring and the plan's latency metric |
| `src/frontier.py` | Patient frontiers, interpolated excess latency (primary endpoint), seed null, pooled endpoint |
| `src/stats.py` | Patient bootstrap, mixed-effects model, concentration, H3 dwell time and error autocorrelation |
| `src/devices.py` | cpu / cuda / dml / auto device selection |
| `scripts/download_data.py` | Resumable dataset download (CHB-MIT, Siena, SeizeIT2) |
| `scripts/run_patient.py` | Runs (fold, seed) jobs for any `--dataset`, `--model`, `--arm`; parallel, resumable, safe to run several at once |
| `scripts/analyze_frontier.py` | Summary tables, frontier plots, gate checks, the Stage 0 kill rule |
| `scripts/analyze_stats.py` | Stage 1 statistics: bootstrap intervals, mixed model, concentration, H3, FP/h ratio per patient |
| `tests/test_core.py` | Correctness tests (scoring, alarm timing, folds, BN folding, quantization, QAT, endpoint, statistics, dataset counts) |
| `runs/` | Outputs: `stage0/GATE.md` is the pipeline-gate report |

Every implementation choice the plan or EpiDeNet leaves open is listed in the docstring at the top of the module that makes it.

## Setup

Python 3.12. Versions in `requirements.txt` are the tested ones.

**Linux workstation, cluster, or WSL2** (CPU, or NVIDIA with a CUDA build of torch):

```bash
bash scripts/setup_wsl.sh            # builds ~/venvs/eegcv and runs the tests
source ~/venvs/eegcv/bin/activate
```

For NVIDIA, set `TORCH_INDEX` to the CUDA wheel index pytorch.org lists for your driver before running the script.

**Windows with an AMD/Intel GPU (DirectML)**, used on the laptop:

```bash
uv venv --python 3.12 .venv-dml
uv pip install --python .venv-dml/Scripts/python.exe torch-directml==0.2.5.dev240914 -r requirements.txt
.venv-dml/Scripts/python.exe -m pytest tests -q
```

`torch-directml` pins torch 2.4.1; the tests pass on it.

**Data:** `python scripts/download_data.py chbmit` (also `siena`, `seizeit2`). Datasets land in `data/`. Re-running resumes.

## Running

```bash
python -m pytest tests -q                                            # always first on a new machine
python scripts/run_patient.py --patients all --seeds 0 1 2 --workers 2 --threads 4    # Stage 0, pinned
python scripts/analyze_frontier.py --runs runs/stage0
python scripts/analyze_stats.py --runs runs/stage0
```

Later stages use the same runner (see its docstring for more):

```bash
python scripts/run_patient.py --patients all --seeds 0 1 2 3 4 --out runs/stage1                 # 5 seeds
python scripts/run_patient.py --model ahlawat --patients all --out runs/stage1_ahlawat           # secondary model
python scripts/run_patient.py --arm cross --out runs/stage1_cross                                # leave one group out
python scripts/run_patient.py --dataset siena --patients all --out runs/stage2_siena             # replication
python scripts/run_patient.py --dataset seizeit2 --patients all --out runs/stage3_seizeit2       # wearable
```

Patients with fewer than 3 usable seizure records are skipped with a message (the fold design needs a test, a validation and a training fold).

- **Threads are pinned at 4 per job** (the default) for Stage 0 and the chb01 pilot: the thread count changes results slightly (see Reproducibility), so never mix values within a run.
- **Workers.** This model is tiny, so throughput comes from running jobs in parallel: `--workers` x 4 threads should not exceed the CPU threads available (8 under the laptop's WSL2 setup, hence 2 workers). Each GPU worker (`--gpu-workers`, exploratory runs only) trains on the GPU and does quantization and scoring on the CPU.
- **Memory.** A job holds its patient's cached signals (about 0.3 GB per 40 h of recording) plus one record's evaluation windows at a time. The longest patient, chb04 (156 h), needs about 1.2 GB of signal; budget about 2 GB per worker with Python and torch overhead. Most patients need well under 1 GB.
- **Cache.** `--cache` (default `~/eegcv_cache/chbmit`) should be on a local disk. Under WSL, keep it in the Linux filesystem: reading from `/mnt/c` is slow.
- **Several runners / machines.** Jobs are claimed with `<job>.claim` files, so CPU and GPU runners, or several machines sharing `--out`, never duplicate work. After a crash, restart once with `--clear-claims` (only when no other runner is active).
- **Outputs per job:** `fold<k>_seed<s>.json` (summary, frontier rows, thresholds, timing, software and hardware), `.npz` (raw validation and test scores of every model; the trained FP32 weights and normalization, which `pipeline.load_fp32` turns back into the model; the QAT weights and activation ranges), `.log`.
- **Models per job:** FP32; post-training ONNX INT8 (primary); simulated 8/6/4-bit (dose-response and INT8 cross-check); quantization-aware 8-bit fine-tuned from the FP32 model (`qat8`, read against the seed band only).

## Reproducibility

- **The CPU thread count is part of the environment.** Floating-point addition is not associative, and different `--threads` values split each sum differently, so training drifts to a slightly different model (chb01 fold 0: 4 vs 8 threads gave score correlation 0.995, like a small seed change). Stage 0 and the pilot use 4; each job records it (`environment.cpu_threads`).
- **Confirmatory environment (Stage 0):** WSL2 Ubuntu, Python 3.12, torch 2.14.1 CPU build, packages as in `requirements.txt`, 4 threads per job, CPU only.
- A job is deterministic on a given device, software stack and thread count: re-running it reproduces every number exactly (checked on Linux CPU with torch 2.14.1 and on DirectML with torch 2.4.1; CUDA runs use deterministic cuDNN settings but have not been tested here).
- **Different devices or torch versions train slightly different models**, much like a different seed (on one chb01 fold: identical alarm counts and latencies, window AUROC 0.979 on CPU vs 0.995 on DirectML). The primary comparison is paired inside each job, so it is unaffected; each job records its device and versions, so the seed null can be restricted to same-device pairs as a sensitivity check. The confirmatory Stage 0 run therefore uses the single pinned environment above.
- The ONNX export uses the TorchScript exporter (`dynamo=False`), which newer torch releases deprecate; keep torch pinned.

## Dataset notes

- CHB-MIT: 686 records, 141 of them with seizures, 198 seizures. Three chb12 records (13 seizures) use another montage without the four temporal channels, leaving 683 usable records, 138 seizure records (so 138 patient-specific folds) and 185 seizures. chb17's records are named `chb17a_*`, `chb17b_*`, `chb17c_*`.
- Seizure times come from the summary files. They agree with the `.seizures` annotation files except for chb24_21 (summary onset 2804 s, annotation 2404 s). `RECORDS-WITH-SEIZURES` wrongly lists chb07_18 instead of chb07_19; the pipeline does not use that list.
- chb21 is the same subject as chb01, recorded 1.5 years later (PhysioNet's description; `SUBJECT-INFO` lists F, 11 and F, 13): the cross-patient (leave-one-patient-out) arm must keep them on the same side of every split.
- Onsets and offsets are annotated in whole seconds.
- Cross-patient arm: 23 groups (chb01 + chb21 together), 683 records, 185 seizures. A job trains on about 100,000 windows (about 27 times a patient-specific job), so this arm is cluster-sized.
- Siena: 14 patients, 41 records, 47 seizures (all parsed; two corrections in `src/siena.py`: PN01's list names a file "PN01.edf", and PN00-3's listed seizure end 19.29.29 falls after the recording and is read as 18.29.29). Every record contains a seizure, and only 8 patients have 3+ records (37 seizures), so only they fit the record-wise fold design.
- SeizeIT2: 125 subjects, 2,850 recordings, 11,626 h, 883 seizures, two behind-the-ear channels whose pair varies by recording; each subject uses its main pair. 53 subjects have 3+ seizure records in it (734 seizures).
