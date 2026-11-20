# OSF registration update 4: details left open in update 3

**Status:** submitted on OSF on 2026-11-17, before the workstation run started. It fills in what update 3 left in brackets, from the repeatability check. Same mechanics as before: each paragraph was appended to the end of its field.

## Justification tab

> Fourth update, submitted before the confirmatory run on the workstation started. It records details that update 3 (2026-11-17) left open until the workstation was set up and checked; nothing in the design, analysis or decision rule changes. Ahlawat results seen so far: none.

## Page 6: Analysis Plan → Inference criteria (add at the end)

> Update 4. Code for the confirmatory run: commit 58d8708. Repeatability check (registered in update 3) passed on 2026-11-17: chb01, fold 0, seed 0, run twice on the workstation, gave identical saved weights and test scores, compared array by array without inspecting any metric; both outputs were then deleted, and the job is rerun as part of the confirmatory run. Concurrency: 2 jobs per GPU (one runner per GPU, --gpu-workers 2), 4 jobs at a time, 4 CPU threads each (16 of the 16 physical cores). The laptop's 236 partial jobs are analysed only after the confirmatory analysis is complete, as the hardware-reproducibility check of update 3.

## Page 7: Other (add at the end)

> Update 4. Measured time per job on the workstation: 655 s and 648 s for the two repeatability runs (56 min for the same job on the laptop). Expected duration of the 690 jobs: about 1.5-2.5 days. Correction to update 3: at the measured pace, the laptop run would have taken about 18-19 days in total (690 jobs at a mean of 77 min, two at a time), not 12-14. Run command per GPU i (CUDA_VISIBLE_DEVICES=i): run_patient.py --model ahlawat --patients all --seeds 0 1 2, then --seeds 3 4, with --workers 0 --gpu-workers 2 --gpu-device cuda --threads 4 --out runs/stage1_ahlawat_ws.
