# Linking detection delay to patient outcome (literature notes, 2026-11-24)

*Response to the advisor's suggestion to "tie delay to an outcome, e.g. survivability". Working notes for the Discussion; not a result of this study and not registered. Sources were found through PubMed and checked against their abstracts; DOIs given. Not yet a systematic search (see `paper/LIT_REVIEW_PROTOCOL.md`).*

## What the literature supports

**1. Time to treatment matters on a scale of minutes, for prolonged seizures.**
- Gaínza-Lein et al. 2018, JAMA Neurology (doi:10.1001/jamaneurol.2017.4382): prospective multicentre cohort, 218 children with refractory convulsive status epilepticus. First benzodiazepine 10 min or more after onset (66% of patients) was independently associated with death (adjusted OR 11.0, 95% CI 1.43 to infinity), continuous infusions (1.8), longer convulsions (2.6) and hypotension (2.3).
- Gaínza-Lein et al. 2019, Seizure (doi:10.1016/j.seizure.2018.05.021): review of 15 studies (2,212 patients): average time to treatment 42.4 min; later treatment linked to benzodiazepine resistance, longer seizures and higher in-hospital mortality.
- Sánchez Fernández et al. 2018, Neurology (doi:10.1212/WNL.0000000000005488): median 16 min from onset to first benzodiazepine; out-of-hospital onset independently associated with longer delays (HR 1.5). Recognition, not drug choice, is the first bottleneck, which is what an alarm addresses.

**2. SUDEP: death follows a generalized tonic-clonic seizure within minutes, mostly at night and unwitnessed; supervision is protective.**
- Ryvlin et al. 2013, MORTEMUS, Lancet Neurology (doi:10.1016/S1474-4422(13)70214-X): in monitored SUDEP cases, cardiorespiratory dysfunction began within 3 min after a generalized tonic-clonic seizure, with terminal apnoea within 11 min of seizure end; 14 of 16 SUDEPs at night; the authors call for better supervision.
- Langan et al. 2005, Neurology (doi:10.1212/01.WNL.0000156352.61328.CB): case-control, 154 SUDEP cases. Night-time supervision protective (OR 0.4, 0.2-0.8); a listening device or similar precaution OR 0.1 (0.0-0.3).
- Lamberts et al. 2012, Epilepsia (doi:10.1111/j.1528-1167.2011.03360.x): SUDEP mostly sleep-related (58%) and unwitnessed (86%); nocturnal seizures an independent risk factor (OR 2.6).

**3. Guidelines value alarms only where they lead to rapid intervention, and set the false-alarm scale.**
- Beniczky et al. 2021, ILAE-IFCN clinical practice guideline, Epilepsia (doi:10.1111/epi.16818): recommends validated wearable detection of tonic-clonic seizures "especially in unsupervised patients, where alarms can result in rapid intervention" (weak recommendation); says it is uncertain whether alarms improve clinical outcomes; does not recommend current devices for other seizure types.
- Meritam Larsen et al. 2023, Epilepsy & Behavior (doi:10.1016/j.yebeh.2023.109486): validated non-EEG wearables detect 79.4-96% of tonic-clonic seizures at 0.20-1.92 false alarms per 24 h.

## What this means for this study (honest framing)

1. **Seconds are not the relevant unit; minutes are.** The clinically documented windows are about 3-11 min (SUDEP after a tonic-clonic seizure) and 10 min (first benzodiazepine). INT8's excess latency (-0.13 s, 95% CI -0.30 to 0.00 s) is negligible on that scale, and even simulated 4-bit's +16 s is small next to them. Claiming that a 16 s delay changes survival would overstate the evidence; no study quantifies outcome per second of detection delay.
2. **Missed seizures and false alarms matter more than seconds.** The outcome evidence is about whether someone is alerted at all (supervision, OR 0.1-0.4) and whether alarms are trusted. That is what the false-alarm-capped sensitivity analysis measures: at the guideline-scale caps (0.5-2 per 24 h), INT8 lost no sensitivity, while 4-bit activations lost a large share (CHB-MIT, Ahlawat: pooled sensitivity 0.30-0.39 against FP32's 0.58-0.66). The outcome link is therefore strongest through sensitivity at a fixed false-alarm budget, not through latency.
3. **Scope limit.** CHB-MIT and Siena seizures are mostly focal or EEG-defined, not the tonic-clonic seizures for which outcome evidence and guideline recommendations exist. Any outcome statement must say so.

## Possible illustrative calculation (modelled, if the paper wants one)

A transparent "missed alarms per patient-year" calculation, not a survival estimate: seizures per year x (FP32 sensitivity - quantized sensitivity at the same false-alarm cap) = additional unalerted seizures per year, under stated assumptions (seizure frequency from the literature, tonic-clonic share, caps from the guideline range). This needs a seizure-frequency source (not yet searched) and must be labelled as a model. Converting it to deaths (via SUDEP incidence and the supervision odds ratio) stacks several assumptions and is not recommended.

## Suggested Discussion sentence

"Clinical evidence ties outcome to whether a seizure is alerted and treated within minutes (Gaínza-Lein 2018; Ryvlin 2013; Langan 2005), not to seconds of detection delay; on that scale INT8 is negligible, and the clinically relevant cost of aggressive quantization is the sensitivity lost at a fixed false-alarm budget."
