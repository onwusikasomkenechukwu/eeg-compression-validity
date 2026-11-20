# OSF registration update 3: confirmatory run moved to a GPU workstation

**Status:** submitted on OSF on 2026-11-17, with the laptop run analysed only after the confirmatory analysis (the wording below). The laptop run was stopped for good the same day (queue first, so seeds 3-4 never started); its 236 finished jobs are set aside unopened in `runs/stage1_ahlawat/`. Items still in brackets (commit, per-job time, jobs at a time) came from the repeatability check (2026-11-17: two runs of chb01 fold 0 seed 0 gave identical saved arrays; 655 s and 648 s; outputs deleted, metrics not inspected) and are added to OSF as a short note before the run starts. Same mechanics as updates 1 and 2: append each paragraph to the end of its field; cite the commit.

## Justification tab

> Third update. On 2026-11-17 the advisor gave access to a GPU workstation (2 x NVIDIA RTX 4090, 24 GB each). Update 2 fixed one environment for the whole confirmatory run (the development laptop, WSL2, CPU only); at the measured pace that run would take about 18-19 days in total (690 jobs at a mean of 77 min, two at a time). The run was paused on 2026-11-17 at 236 of 414 jobs of seeds 0-2. No result of those jobs was inspected: only the runner's log (job completion, run time, errors) was read. The confirmatory run is restarted from scratch on the workstation, all 690 jobs (seeds 0-4) in one environment fixed below, decided before any Ahlawat result has been seen. The analysis plan, decision rule, fidelity check and interim report of update 2 are unchanged. The laptop's partial run is not part of the confirmatory test; it is analysed only after the confirmatory analysis is complete (see Exploratory analysis).

## Page 6: Analysis Plan → Inference criteria (add at the end)

> Update 3. The confirmatory run of update 2 (seeds 0-4, 690 jobs) is run on a GPU workstation instead of the laptop, with everything else as registered in update 2. Environment fixed for the whole run: Ubuntu 26.04.1 LTS, Python 3.12.15, torch 2.14.1+cu132 (CUDA 13.2, cuDNN 9.24.0), NVIDIA driver 595.99.02, 2 x RTX 4090 (24 GB), AMD Ryzen Threadripper PRO 5955WX (16 cores, 32 threads), 123 GB RAM, package versions as in requirements.txt apart from the torch build; code at commit 58d8708. FP32 training and 8-bit quantization-aware training run on the GPU with cuDNN's deterministic mode; post-training quantization (ONNX Runtime INT8; simulated 8-, 6- and 4-bit; W4A8; FP16) and all scoring run on the CPU with 4 threads per job, as on the laptop. One runner per GPU; runners share the output folder and claim jobs exclusively, so each job runs once. Before the run, a repeatability check: one job (chb01, fold 0, seed 0) run twice on the workstation must give identical saved weights and test scores (compared by hash, without inspecting metrics); its outputs are then deleted and the job is rerun as part of the confirmatory run. If it is not repeatable, the run does not start and this is reported. Seeds 0-2 and 3-4 may run concurrently; the interim report of update 2 (seeds 0-2) is still allowed and still makes no decision. Because results on a GPU are not bit-identical to the CPU, all 690 jobs use the workstation; no job from the laptop run is mixed in.

## Page 6: Analysis Plan → Exploratory analysis (add at the end)

> Update 3. The laptop's partial run (236 jobs of seeds 0-2, CPU) is set aside, unopened, and analysed only after the confirmatory analysis is complete: (1) as a hardware-reproducibility check, comparing each of its jobs with the same patient, fold and seed on the workstation (FP32 test AUROC, specificity at the threshold, and INT8 excess latency); (2) any other use is labelled exploratory.

## Page 7: Other (add at the end)

> Update 3: code at commit 58d8708; run on 2 x RTX 4090 (`run_patient.py --model ahlawat --patients all --seeds 0 1 2 3 4 --workers 0 --gpu-workers 2 --gpu-device cuda --threads 4 --out runs/stage1_ahlawat_ws`, one runner per GPU via CUDA_VISIBLE_DEVICES, so 4 jobs at a time). Measured time per job on the workstation: 10.9 and 10.8 min for the two repeatability runs (chb01, fold 0, seed 0; 56 min on the laptop), so about 1.5-2.5 days for the 690 jobs at 4 at a time.

---

## Checklist before submitting

1. **Set up the workstation.** Clone the repo at the current main; create a venv with requirements.txt and the CUDA build of torch; download CHB-MIT with `scripts/download_data.py` (checksums verified); run the tests.
2. **Repeatability check.** Run chb01 fold 0 seed 0 twice; compare the saved weights (npz) and test scores by hash only. Do not open the JSON metrics. Record the per-job time. Delete both outputs.
3. **Code changes, if any** (for example, if determinism needs `torch.use_deterministic_algorithms`): commit them, rerun the tests, and cite that commit. None are expected: the CUDA path, cuDNN determinism and multi-runner claims already exist.
4. **Fill the brackets** with the environment from step 1 and the timing from step 2. Ask Aryal to read it (his workstation; the change of environment).
5. **Submit, then start.** Leave the laptop run paused (or stop it) and do not open its outputs.

Open decision for the user: whether the 236 laptop jobs are analysed before this update (then they must be disclosed here as seen, which weakens the restart's claim that no result was seen) or only after the confirmatory analysis (this draft's wording).
