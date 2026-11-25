"""EEGformer fidelity check C (update 8): the protocol-matched check on chb01-chb08 against the
published CHB-MIT results (Busia et al. 2024, Table IV: 32/44 seizures detected, 0.15 FP/h with
consecutive false positives counted as one event, median 0 FP/h over the 40 test records,
average latency 15.2 s).

The rule mirrors the registered EpiDeNet check (scripts/sanity_gate.py): pooled over patients,
averaged over seeds, both parts must pass.
  A. seizures detected >= 1 - 2 x (12/44) = 0.455 (the published miss rate doubled)
  B. event false positives per hour within [0.075, 0.30] (the published 0.15, factor of 2)
Descriptive (not criteria): segment-level sensitivity, median per-record FP/h, mean latency.

Usage: python scripts/eegformer_gate.py --runs runs/eegformer_check   -> <runs>/fidelity_check_c.md
"""
import argparse
import glob
import json
import os
from collections import defaultdict

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PUBLISHED = {"detected": 32, "seizures": 44, "fp_per_h": 0.15, "segment_sens": 0.655, "latency_s": 15.2}
DETECT_MIN = 1 - 2 * (1 - PUBLISHED["detected"] / PUBLISHED["seizures"])
FPH_RANGE = (PUBLISHED["fp_per_h"] / 2, PUBLISHED["fp_per_h"] * 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=os.path.join(ROOT, "runs", "eegformer_check"))
    args = ap.parse_args()
    per_seed = defaultdict(lambda: defaultdict(list))
    for p in sorted(glob.glob(os.path.join(args.runs, "chb*", "fold*_seed*.json"))):
        s = json.load(open(p))
        if s.get("protocol") != "eegformer":
            raise SystemExit(f"{p}: not an EEGformer-protocol job")
        for c in s["check"]:
            per_seed[s["seed"]]["rec"].append(c)
    if not per_seed:
        raise SystemExit(f"no finished jobs in {args.runs}")
    rows = []
    for seed, d in sorted(per_seed.items()):
        r = d["rec"]
        det, sz = sum(c["detected"] for c in r), sum(c["seizures"] for c in r)
        hours = sum(c["hours"] for c in r)
        fph = sum(c["fp_events"] for c in r) / hours
        seg = sum(c["seizure_windows_detected"] for c in r) / max(sum(c["seizure_windows"] for c in r), 1)
        med = float(np.median([c["fp_events"] / c["hours"] for c in r]))
        lat = [x for c in r for x in c["latencies_s"]]
        rows.append((seed, len(r), det, sz, det / sz, fph, med, seg, float(np.mean(lat)) if lat else float("nan"), hours))
    det = float(np.mean([x[4] for x in rows]))
    fph = float(np.mean([x[5] for x in rows]))
    pa, pb = det >= DETECT_MIN, FPH_RANGE[0] <= fph <= FPH_RANGE[1]
    lines = ["# EEGformer fidelity check C (protocol-matched, chb01-chb08; registered in update 8)", "",
             "| seed | test records | seizures detected | detection rate | event FP/h | median record FP/h "
             "| segment sensitivity | mean latency (s) | hours |", "|---|---|---|---|---|---|---|---|---|"]
    lines += [f"| {s} | {n} | {d}/{z} | {r:.3f} | {f:.3f} | {m:.3f} | {g:.3f} | {l:.1f} | {h:.0f} |"
              for s, n, d, z, r, f, m, g, l, h in rows]
    lines += ["", f"Mean over seeds: detection {det:.3f} (pass if >= {DETECT_MIN:.3f}): **{'PASS' if pa else 'FAIL'}**; "
              f"event FP/h {fph:.3f} (pass if within [{FPH_RANGE[0]:.3f}, {FPH_RANGE[1]:.2f}]): **{'PASS' if pb else 'FAIL'}**.",
              "", f"Check C: **{'PASS' if pa and pb else 'FAIL'}**. Published (Table IV): 32/44 detected (0.727), "
              "0.15 FP/h, median 0 FP/h, segment sensitivity 0.655, latency 15.2 s."]
    out = os.path.join(args.runs, "fidelity_check_c.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
