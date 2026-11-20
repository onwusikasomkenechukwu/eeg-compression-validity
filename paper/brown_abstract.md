# NRCB 2027 abstract (draft for advisor review)

Early submission deadline: January 10, 2027 (free; $60 by January 17 if accepted). Conference: March 20, 2027, in person. Limit: 300 words.

Status (2026-11-19): complete (revised: confirmatory CI read as an upper bound; fidelity check named). Possible later addition: if Ahlawat's W4A8 rescore also costs little, extend the W4A8 sentence to both detectors (needs matching cuts). EpiDeNet numbers are exploratory, as registered; the Ahlawat sentence is the confirmatory result (all 690 jobs on the workstation, OSF updates 3-5; fidelity check B passed, 87 of 120 patient-seeds). 299 words. Pending: advisor review, and the update 5 repeatability check (it cannot change the result).

**Title:** Does Compressing a Wearable Seizure Detector Change When It Alarms? A Pre-Registered Test of 8-Bit Quantization

**Co-authors:** Somkene Onwusika [university]; Saurav Aryal [university, department]

**Research category:** [pick from the form's list; closest is likely biomedical or translational science]

**Oral presentation:** [yes / no]

## Abstract

Wearable seizure detectors must run on microcontrollers, so their neural networks are compressed, typically to 8-bit integers (INT8). Compressed models are certified with window-level metrics such as AUROC, sensitivity and specificity, which ignore time order and cannot show whether compression changes false alarms or alarm timing. Of 14 compression studies we reviewed, none compared event-level false alarms or latency before and after compression.

We pre-registered a test of whether quantization moves a detector along its false-alarm/latency trade-off. We reimplemented EpiDeNet, a four-channel wearable detector, and trained patient-specific models on the CHB-MIT dataset (24 cases, 185 seizures; 414 models over 3 seeds), comparing each with compressed versions of the same weights. The primary outcome was excess latency: how much later the compressed model must alarm to match the original's false-alarm rate.

INT8 showed no measurable shift: excess latency was 0.22 seconds (95% CI 0.00-0.67), within seed-to-seed variation, and seizure sensitivity at caps of 0.5, 1 and 2 false alarms per day was unchanged. 4-bit weights with 8-bit activations cost 0.5 seconds. Simulated 4-bit throughout, which mainstream microcontrollers cannot run natively, delayed alarms by 20.7 seconds and lowered sensitivity at every cap. These results are exploratory: our reimplementation did not reproduce EpiDeNet's published false-alarm rate under either of two protocols. In the pre-registered confirmatory test on a second published detector (Ahlawat, 2026; 690 models over 5 seeds; fidelity check passed), INT8 excess latency was -0.13 seconds (95% CI -0.30 to 0.00), ruling out delays above 0.3 seconds: the hypothesis was not supported, sensitivity at every cap was unchanged, and simulated 4-bit again delayed alarms (16.2 seconds).

INT8 appears safe for both detectors, while lower bit widths cost alarm time. Both conclusions require time-ordered, event-level evaluation, which window-level certification lacks. We propose evaluating compressed detectors by recall under a fixed false-alarm cap.
