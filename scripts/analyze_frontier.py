"""Summarize saved runs: frontiers, excess latency per quantized model, the FP32 seed band,
and EpiDeNet-comparable FP32 numbers for the sanity gate.

Usage: python scripts/analyze_frontier.py [--runs runs/stage0] [--patients chb01 ...]
Writes <runs>/summary.md, <runs>/excess_latency.csv and <runs>/<patient>_frontier.png.
"""
import argparse
import csv
import glob
import json
import math
import os
import sys
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from frontier import (DEFAULT_SMOOTH, band_95, excess_latency, operating_point, patient_frontier,  # noqa: E402
                      pooled_excess, seed_band)
from pipeline import SPEC_TOLERANCE, TARGET_SPEC  # noqa: E402

QUANT = ["int8", "sim8", "sim6", "sim4", "qat8"]  # qat8: retrained, read against the seed band only
LATENCY_FLOOR_S = 2.0  # pre-registration draft, section 2
KILL_MODELS = ("int8", "sim6", "sim4")  # sim8 only cross-checks the ONNX INT8 path


def fmt(x, nd=1):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    return "inf" if x == math.inf else f"{x:.{nd}f}"


def load_runs(runs, patients):
    by = defaultdict(lambda: defaultdict(list))  # patient -> seed -> [summary]
    for path in sorted(glob.glob(os.path.join(runs, "*", "fold*_seed*.json"))):
        s = json.load(open(path))
        if patients and s["patient"] not in patients:
            continue
        by[s["patient"]][s["seed"]].append(s)
    return by


def pooled_specificity(runs_dir, patient, jobs):
    """FP32 window specificity over all of a patient's held-out hours for one seed, from the
    saved scores (each fold at its own threshold). Returns (specificity, within the band)."""
    import numpy as np
    neg = correct = 0
    for s in jobs:
        a = np.load(os.path.join(runs_dir, patient, f"fold{s['fold']}_seed{s['seed']}.npz"))
        bg = a["test_labels"] == 0
        neg += int(bg.sum())
        correct += int((bg & (a["test_fp32"] <= s["thresholds"]["fp32"])).sum())  # alarm only above the threshold
    spec = correct / neg
    return spec, abs(spec - TARGET_SPEC) <= SPEC_TOLERANCE


def plot_frontier(path, fronts, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    colors = {"fp32": "#222222", "int8": "#1f6fb4", "sim8": "#7fb2e5", "sim6": "#e08a1e", "sim4": "#c0392b",
              "qat8": "#2e8b57"}
    for (seed, variant), pts in sorted(fronts.items()):
        xs = [p["median_latency_s"] for p in pts if math.isfinite(p["median_latency_s"])]
        ys = [p["fa_per_24h"] for p in pts if math.isfinite(p["median_latency_s"])]
        ax.plot(xs, ys, "-o", ms=3, lw=1, color=colors[variant], alpha=0.85,
                label=variant if seed == min(s for s, _ in fronts) else None)
        op = operating_point(pts)
        if math.isfinite(op["median_latency_s"]):
            ax.plot(op["median_latency_s"], op["fa_per_24h"], "s", ms=6, mfc="none", color=colors[variant])
    ax.set_xlabel("median detection latency (s)")
    ax.set_ylabel("false alarms per 24 h (SzCORE)")
    ax.set_title(title, fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=os.path.join(ROOT, "runs", "stage0"))
    ap.add_argument("--patients", nargs="*")
    args = ap.parse_args()

    by = load_runs(args.runs, args.patients)
    md = ["# Stage 0 summary", ""]
    csv_rows = []
    all_null, all_excess = [], defaultdict(lambda: defaultdict(dict))  # model -> patient -> seed -> s

    for patient, seeds in sorted(by.items()):
        n_folds = {s: len(v) for s, v in seeds.items()}
        md += [f"## {patient}", "", f"Folds per seed: {n_folds}", ""]

        # Checks.
        rows = [s for v in seeds.values() for s in v]
        early = sum(s["timing"]["stopped_early"] for s in rows)
        diff = max(s["onnx_fp32_max_abs_logit_diff"] for s in rows)
        md += [f"- Early stopping fired in {early}/{len(rows)} jobs; ONNX FP32 export max |logit diff| {diff:.2e}"]
        for seed, runs in sorted(seeds.items()):
            spec, ok = pooled_specificity(args.runs, patient, runs)
            md.append(f"- Seed {seed}: FP32 test specificity pooled over all held-out hours {spec:.4f} "
                      f"({'within' if ok else 'OUTSIDE'} {TARGET_SPEC} +/- {SPEC_TOLERANCE})")
        out_band = [(s["fold"], s["seed"], round(s["window"]["fp32"]["specificity"], 4)) for s in rows if not s["spec_in_band"]]
        md += [f"- Diagnostic: single folds outside the band {len(out_band)}/{len(rows)}"
               + (f" {out_band}" if out_band else ""), ""]

        # EpiDeNet-comparable FP32 numbers, pooled over folds, per seed.
        md += ["### FP32 against EpiDeNet's reporting (4 s windows, pooled over folds)", "",
               "| seed | FP/h raw | FP/h 3-window vote | window sens (vote) | spec (vote) | seizures detected |",
               "|---|---|---|---|---|---|"]
        for seed, runs in sorted(seeds.items()):
            e = [r["window"]["fp32"]["epidenet"] for r in runs]
            h = sum(x["hours"] for x in e)
            fp_raw = sum(x["fp_per_h_raw"] * x["hours"] for x in e) / h
            fp_vote = sum(x["fp_per_h_vote"] * x["hours"] for x in e) / h
            det, sz = sum(x["seizures_detected"] for x in e), sum(x["seizures"] for x in e)
            sens = sum(x["sens_vote"] for x in e) / len(e)
            spec = sum(x["spec_vote"] for x in e) / len(e)
            md.append(f"| {seed} | {fp_raw:.2f} | {fp_vote:.2f} | {sens:.3f} | {spec:.4f} | {det}/{sz} |")
        md += ["", "EpiDeNet (all CHB-MIT, LOOCV, 5 seeds): 4.29 raw, 2.24 with vote, 165/181 seizures.", ""]

        # Same model, same threshold: window-counted "FP/h" vs SzCORE false alarms per hour.
        md += ["### Two meanings of \"FP/h\" for the same FP32 model (pooled over folds)", "",
               "| seed | window FP/h (3-window vote, 4 s grid) | SzCORE false alarms/h (12 s smoothing) | ratio |",
               "|---|---|---|---|"]
        for seed, runs in sorted(seeds.items()):
            e = [r["window"]["fp32"]["epidenet"] for r in runs]
            h = sum(x["hours"] for x in e)
            win_fph = sum(x["fp_per_h_vote"] * x["hours"] for x in e) / h
            ev = [row for r in runs for row in r["frontier"]
                  if row["variant"] == "fp32" and row["smooth_s"] == DEFAULT_SMOOTH]
            ev_fph = sum(x["fp"] for x in ev) / sum(x["hours"] for x in ev)
            md.append(f"| {seed} | {win_fph:.2f} | {ev_fph:.2f} | "
                      f"{fmt(win_fph / ev_fph, 1) if ev_fph else 'n/a'} |")
        md += ["", "Window FP/h is (1 - specificity) x windows per hour, so it depends on window length and "
               "hop, and one long artifact counts many times; SzCORE merges detections within 90 s into one alarm.", ""]

        # Frontiers and excess latency.
        fronts, fp32_by_seed = {}, {}
        md += ["### Operating point (default smoothing, own threshold) and excess latency", "",
               "| seed | model | FA/24h at 12 s | median latency at 12 s | detected | excess latency at FP32's FA (s) | smoothing there (s) | ΔFA/24h at FP32's latency |",
               "|---|---|---|---|---|---|---|---|"]
        for seed, runs in sorted(seeds.items()):
            fr = patient_frontier([row for r in runs for row in r["frontier"]])
            fp32 = fr[("fp32", "own")]
            fp32_by_seed[seed] = fp32
            for variant in ["fp32"] + QUANT:
                if (variant, "own") not in fr:  # e.g. runs made before QAT existed
                    continue
                pts = fr[(variant, "own")]
                fronts[(seed, variant)] = pts
                op = operating_point(pts)
                if variant == "fp32":
                    ex, mw, dfa = 0.0, DEFAULT_SMOOTH, 0.0
                else:
                    ex, mw, dfa = excess_latency(fp32, pts)
                    all_excess[variant][patient][seed] = ex
                    csv_rows.append({"patient": patient, "seed": seed, "model": variant, "threshold": "own",
                                     "excess_latency_s": ex, "matched_smooth_s": mw, "delta_fa_per_24h": dfa})
                    ex2, mw2, dfa2 = excess_latency(fp32, fr[(variant, "fp32")])
                    csv_rows.append({"patient": patient, "seed": seed, "model": variant, "threshold": "fp32",
                                     "excess_latency_s": ex2, "matched_smooth_s": mw2, "delta_fa_per_24h": dfa2})
                md.append(f"| {seed} | {variant} | {fmt(op['fa_per_24h'])} | {fmt(op['median_latency_s'])} | "
                          f"{op['detected']}/{op['seizures']} | {fmt(ex)} | {fmt(mw)} | {fmt(dfa)} |")
        null = seed_band(fp32_by_seed)
        all_null += null
        md += ["", f"FP32 seed-to-seed excess latency (the null), all ordered seed pairs: {[fmt(x) for x in null]}",
               f"95% band: {band_95(null)}", ""]

        png = os.path.join(args.runs, f"{patient}_frontier.png")
        plot_frontier(png, fronts, f"{patient}: false alarms vs latency across smoothing widths (squares: 12 s)")
        md += [f"![{patient} frontier]({os.path.basename(png)})", ""]

    band = band_95(all_null)
    md += ["## Pooled across patients (pre-registered: median over seeds per patient, then over patients)", "",
           f"- FP32 seed-pair null: n = {len(all_null)} ordered pairs, 95% band "
           f"{tuple(round(b, 2) for b in band) if band else None}"]
    stop = True
    for v in QUANT:
        if not all_excess[v]:
            continue
        pooled, per_patient = pooled_excess(all_excess[v])
        vals = [x for seeds in all_excess[v].values() for x in seeds.values()]
        n_cens = sum(x == math.inf for x in vals)
        n_undef = sum(math.isnan(x) for x in vals)
        inside = band is not None and band[0] <= pooled <= band[1]
        below = pooled < LATENCY_FLOOR_S
        if v in KILL_MODELS:
            stop &= inside or below
        md.append(f"- {v}: pooled excess latency {fmt(pooled, 2)} s over {len(per_patient)} patient(s) "
                  f"[{'inside' if inside else 'outside'} the null band, {'below' if below else 'at/above'} the "
                  f"{LATENCY_FLOOR_S:g} s floor]; patient-seed values {len(vals)}, censored {n_cens}, undefined {n_undef}")
    md += ["", f"**Stage 0 kill rule** (stop if INT8, sim6 and sim4 are each inside the band or below "
               f"{LATENCY_FLOOR_S:g} s): {'STOP' if stop else 'CONTINUE'}"
               + (" (pilot: one patient decides nothing)" if len(by) < 2 else "")]

    with open(os.path.join(args.runs, "summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    with open(os.path.join(args.runs, "excess_latency.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(csv_rows[0]) if csv_rows else ["patient"])
        w.writeheader()
        w.writerows(csv_rows)
    print("\n".join(md))


if __name__ == "__main__":
    main()
