# NRCB 2027 abstract (draft for advisor review)

Early submission deadline: January 10, 2027 (free; $60 by January 17 if accepted). Conference: March 20, 2027, in person. Limit: 300 words.

Status (2026-11-10): numbers are Stage 0 (EpiDeNet, exploratory). Before submitting, add the interim result of the registered Ahlawat test (seeds 0-2, due about Nov 20) and, if they add anything, the exploratory W4A8/FP16 results; keep it under 300 words. Present the Ahlawat numbers as interim, as registered.

**Title:** Does Compressing a Wearable Seizure Detector Change When It Alarms? A Pre-Registered Test of 8-Bit Quantization

**Co-authors:** Somkene Onwusika [university]; Saurav Aryal [university, department]

**Research category:** [pick from the form's list; closest is likely biomedical or translational science]

**Oral presentation:** [yes / no]

## Abstract

Wearable seizure detectors must run on microcontrollers, so their neural networks are compressed, typically to 8-bit integers (INT8). Compressed models are certified with window-level metrics such as AUROC, sensitivity and specificity, which ignore time order and cannot show whether compression changes how many false alarms a detector raises or how late it alarms. In a review of 14 compression studies, none compared event-level false alarms or alarm latency before and after compression.

We pre-registered a test of whether quantization moves a detector along its false-alarm/latency trade-off. We reimplemented EpiDeNet, a wearable detector using four temporal EEG channels, and trained patient-specific models on the CHB-MIT dataset (24 cases, 185 seizures; 414 models over 3 seeds). Each model was compared with its INT8 and simulated 6- and 4-bit versions on the same weights. The primary outcome was excess latency: how much later the compressed model must alarm to match the original's false-alarm rate.

INT8 showed no measurable shift: excess latency was 0.22 seconds (95% CI 0.00-0.67), inside the variation between training seeds, and seizure sensitivity at caps of 0.5, 1 and 2 false alarms per day was unchanged. Simulated 4-bit compression, which mainstream microcontrollers cannot run natively, delayed alarms by 20.7 seconds and lowered median sensitivity at every cap. These results are exploratory: our reimplementation did not reproduce EpiDeNet's published false-alarm rate under either our protocol or EpiDeNet's own, which we report as registered. A pre-registered confirmatory test with a second published model (Ahlawat, 2026) is under way. [Interim result, seeds 0-2.]

INT8 appears safe for this detector, while lower bit widths cost alarm time. Either conclusion requires time-ordered, event-level evaluation, which window-level certification does not provide. We propose evaluating compressed detectors by recall under a fixed false-alarm cap.
