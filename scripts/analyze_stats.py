"""Stage 1 statistics on a run folder: patient-bootstrap intervals, mixed-effects model,
concentration, the H3 dwell-time prediction and its premise, and the window-vs-alarm FP/h
ratio per patient.

With --caps, only the exploratory recall-at-false-alarm-cap analysis runs
(prereg/FIDELITY_UPDATE.md item 5), from the job summaries alone:

Usage: python scripts/analyze_stats.py --runs runs/stage0   -> <runs>/stats.md
       python scripts/analyze_stats.py --runs runs/stage0 --caps 0.5 1 2   -> <runs>/caps.md
"""
import argparse
import glob
import json
import math
import os
import sys
from collections import defaultdict

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from frontier import (DEFAULT_SMOOTH, excess_latency, patient_frontier, pooled_excess,  # noqa: E402
                      sensitivity_at_cap)
from stats import (DELTA, DELTA_SENSITIVITY, bootstrap_ci, concentration, dwell, error_autocorr,  # noqa: E402
                   mixed_model, spearman)

MODELS = ["int8", "sim6", "sim4", "qat8"]


def f(x, nd=2):
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else ("inf" if x == math.inf else f"{x:.{nd}f}")


def caps_report(jobs, caps, runs):
    """Recall under false-alarm caps: per patient, seed and model, the best sensitivity among
    smoothing widths at or under the cap (frontier.sensitivity_at_cap). Pooled = seizures
    detected / seizures over the patients where the model reaches the cap, per seed, then the
    median over seeds. Paired change = per patient, the median over seeds (where both reach the
    cap) of the model's sensitivity minus the same seed's FP32; median over patients with a
    patient-bootstrap 95% interval. Patient-seed values where a model never reaches the cap are
    counted, not imputed."""
    models = ["fp32"] + MODELS
    res = defaultdict(dict)  # (patient, seed) -> model -> (detected, seizures, smooth_s) or None
    for patient, seeds in jobs.items():
        for seed, runs_ in seeds.items():
            fr = patient_frontier([row for s, _ in runs_ for row in s["frontier"]])
            for m in models:
                if (m, "own") in fr:
                    res[(patient, seed)][m] = {cap: sensitivity_at_cap(fr[(m, "own")], cap) for cap in caps}
    n = len(res)
    md = [f"# Recall at a false-alarm cap (exploratory): {os.path.relpath(runs, ROOT)}", "",
          f"{len(jobs)} patient(s), {n} patient-seed values per model. SzCORE event sensitivity at the "
          "smoothing width with the most detected seizures among those with false alarms per 24 h at or "
          "below the cap.", ""]
    for cap in caps:
        md += [f"## Cap: {cap:g} false alarms per 24 h", "",
               "| model | pooled sensitivity (median over seeds) | paired change vs FP32 (median of patients) "
               "| 95% patient-bootstrap CI | patients in paired change | cannot reach cap (of patient-seeds) |",
               "|---|---|---|---|---|---|"]
        for m in models:
            vals = {ps: r[m][cap] for ps, r in res.items() if m in r}
            if not vals:
                continue
            by_seed = defaultdict(lambda: [0, 0])
            for (patient, seed), v in vals.items():
                if v is not None:
                    by_seed[seed][0] += v[0]
                    by_seed[seed][1] += v[1]
            pooled = float(np.median([d / z for d, z in by_seed.values() if z])) if by_seed else math.nan
            diffs = defaultdict(list)
            for (patient, seed), v in vals.items():
                ref = res[(patient, seed)]["fp32"][cap]
                if m != "fp32" and v is not None and ref is not None and v[1] and ref[1]:
                    diffs[patient].append(v[0] / v[1] - ref[0] / ref[1])
            per_patient = [float(np.median(d)) for d in diffs.values()]
            change = float(np.median(per_patient)) if per_patient else math.nan
            ci = bootstrap_ci(per_patient) if per_patient else (math.nan, math.nan)
            miss = sum(v is None for v in vals.values())
            md.append(f"| {m} | {f(pooled, 3)} | " + ("n/a | n/a | n/a" if m == "fp32" else
                      f"{f(change, 3)} | [{f(ci[0], 3)}, {f(ci[1], 3)}] | {len(per_patient)}")
                      + f" | {miss}/{len(vals)} |")
        md.append("")
    return md


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=os.path.join(ROOT, "runs", "stage0"))
    ap.add_argument("--caps", nargs="+", type=float, default=None,
                    help="false alarms per 24 h; runs only the recall-at-cap analysis, written to <runs>/caps.md")
    args = ap.parse_args()

    jobs = defaultdict(lambda: defaultdict(list))  # patient -> seed -> [(summary, npz path)]
    for p in sorted(glob.glob(os.path.join(args.runs, "*", "fold*_seed*.json"))):
        s = json.load(open(p))
        jobs[s["patient"]][s["seed"]].append((s, p[:-5] + ".npz"))

    if args.caps:
        md = caps_report(jobs, args.caps, args.runs)
        with open(os.path.join(args.runs, "caps.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(md) + "\n")
        print("\n".join(md))
        return

    excess = defaultdict(lambda: defaultdict(dict))   # model -> patient -> seed -> s
    dw = {d: {} for d in DELTA_SENSITIVITY}           # delta -> patient -> dwell
    acorr = defaultdict(lambda: defaultdict(list))    # model -> lag -> [values]
    fph_ratio = {}
    for patient, seeds in sorted(jobs.items()):
        dwell_by_seed = defaultdict(list)
        win_fp = ev_fp = hours = 0.0
        for seed, runs in sorted(seeds.items()):
            fr = patient_frontier([row for s, _ in runs for row in s["frontier"]])
            for m in MODELS:
                if (m, "own") in fr:
                    excess[m][patient][seed] = excess_latency(fr[("fp32", "own")], fr[(m, "own")])[0]
            sc, lengths = [], []
            for s, npz in runs:
                a = np.load(npz)
                for d in DELTA_SENSITIVITY:
                    dwell_by_seed[d].append((len(a["test_fp32"]), dwell(a["test_fp32"], s["thresholds"]["fp32"], d)))
                for m in ("int8", "sim4"):
                    for lag, r in error_autocorr(a["test_fp32"], a[f"test_{m}"], a["test_lengths"]).items():
                        acorr[m][lag].append(r)
                e = s["window"]["fp32"]["epidenet"]
                win_fp += e["fp_per_h_vote"] * e["hours"]
                hours += e["hours"]
                ev_fp += next(r["fp"] for r in s["frontier"]
                              if r["variant"] == "fp32" and r["smooth_s"] == DEFAULT_SMOOTH)
        for d in DELTA_SENSITIVITY:  # window-weighted over folds, then over seeds
            w = dwell_by_seed[d]
            dw[d][patient] = sum(n * v for n, v in w) / sum(n for n, _ in w)
        fph_ratio[patient] = (win_fp / ev_fp) if ev_fp else math.inf

    md = [f"# Statistics: {os.path.relpath(args.runs, ROOT)}", "",
          f"{len(jobs)} patient(s); seeds per patient: {sorted({len(v) for v in jobs.values()})}", ""]

    md += ["## Excess latency at FP32's false-alarm rate (s)", "",
           "| model | pooled (median of patient medians) | 95% patient-bootstrap CI | mixed model mean [95% CI] | "
           "patient SD | concentration (worst 20%) | censored |", "|---|---|---|---|---|---|---|"]
    for m in MODELS:
        if not excess[m]:
            continue
        pooled, per_patient = pooled_excess(excess[m])
        ci = bootstrap_ci(list(per_patient.values()))
        mm = mixed_model([(p, s, x) for p, seeds in excess[m].items() for s, x in seeds.items()])
        cens = sum(x == math.inf for seeds in excess[m].values() for x in seeds.values())
        md.append(f"| {m} | {f(pooled)} | [{f(ci[0])}, {f(ci[1])}] | "
                  + (f"{f(mm['mean'])} [{f(mm['ci'][0])}, {f(mm['ci'][1])}] | {f(mm['patient_sd'])}"
                     if mm else "n/a (fewer than 3 patients) | n/a")
                  + f" | {f(concentration(list(per_patient.values())))} | {cens} |")

    md += ["", f"## H3: FP32 dwell near the threshold predicts each patient's shift", "",
           f"Dwell = share of FP32 test windows within {DELTA} logits of the FP32 threshold (pre-registered "
           f"width; others are sensitivity analyses). Spearman correlation across patients with the patient's "
           f"median excess latency.", "",
           "| model | " + " | ".join(f"rho, delta={d}" for d in DELTA_SENSITIVITY) + " |",
           "|---|" + "---|" * len(DELTA_SENSITIVITY)]
    for m in MODELS:
        if not excess[m]:
            continue
        _, per_patient = pooled_excess(excess[m])
        pats = sorted(per_patient)
        md.append(f"| {m} | " + " | ".join(
            f(spearman([dw[d][p] for p in pats], [per_patient[p] for p in pats])) for d in DELTA_SENSITIVITY) + " |")
    md += ["", "Per-patient dwell (delta = 0.5): "
           + ", ".join(f"{p} {dw[DELTA][p]:.4f}" for p in sorted(dw[DELTA])), ""]

    md += ["## H3 premise: quantization error over time", "",
           "Autocorrelation of (quantized - FP32) logit differences within test records, median over jobs:", "",
           "| model | lag 1 s | lag 2 s | lag 4 s | lag 8 s |", "|---|---|---|---|---|"]
    for m in ("int8", "sim4"):
        md.append(f"| {m} | " + " | ".join(f(float(np.nanmedian(acorr[m][lag]))) for lag in (1, 2, 4, 8)) + " |")
    md += ["", "Overlapping windows share 3 of 4 s of input at lag 1 s, so some correlation at short lags is "
           "expected from the input alone; the question is how fast it decays relative to the smoothing width.", ""]

    md += ["## Window-counted FP/h vs SzCORE false alarms (FP32, 12 s smoothing), per patient", "",
           ", ".join(f"{p} {f(r, 1)}x" for p, r in sorted(fph_ratio.items())), "",
           f"Median ratio {f(float(np.median([r for r in fph_ratio.values() if math.isfinite(r)])), 1)}x "
           f"over {sum(math.isfinite(r) for r in fph_ratio.values())} patient(s) with at least one alarm.", ""]

    out = os.path.join(args.runs, "stats.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
