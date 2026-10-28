"""The pre-registered FP32 sanity gate (OSF registration, Inference criteria), applied to a run.

EpiDeNet's own definitions (4 s non-overlapping windows, causal 2-of-3 vote; a seizure is
detected when a voted-positive window lies at least half inside it), pooled over all patients
and averaged over seeds. Both parts must pass:
  A. seizures detected >= 82.3% of usable seizures (EpiDeNet's 8.8% miss rate doubled)
  B. voted window false positives per hour within [1.12, 4.48] (EpiDeNet's 2.24, factor of 2)

Usage: python scripts/sanity_gate.py --runs runs/stage0
"""
import argparse
import glob
import json
import os
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DETECT_MIN = 0.823
FPH_RANGE = (1.12, 4.48)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=os.path.join(ROOT, "runs", "stage0"))
    args = ap.parse_args()

    per_seed = defaultdict(lambda: {"det": 0, "sz": 0, "fp_hours": 0.0, "hours": 0.0, "jobs": 0})
    for p in glob.glob(os.path.join(args.runs, "*", "fold*_seed*.json")):
        s = json.load(open(p))
        e = s["window"]["fp32"]["epidenet"]
        a = per_seed[s["seed"]]
        a["det"] += e["seizures_detected"]
        a["sz"] += e["seizures"]
        a["fp_hours"] += e["fp_per_h_vote"] * e["hours"]
        a["hours"] += e["hours"]
        a["jobs"] += 1

    rows = []
    for seed, a in sorted(per_seed.items()):
        rows.append((seed, a["jobs"], a["det"], a["sz"], a["det"] / a["sz"], a["fp_hours"] / a["hours"], a["hours"]))
    det = sum(r[4] for r in rows) / len(rows)
    fph = sum(r[5] for r in rows) / len(rows)
    pass_a, pass_b = det >= DETECT_MIN, FPH_RANGE[0] <= fph <= FPH_RANGE[1]

    lines = ["# FP32 sanity gate (pre-registered)", "",
             "| seed | jobs | seizures detected | detection rate | voted window FP/h | hours |", "|---|---|---|---|---|---|"]
    lines += [f"| {s} | {j} | {d}/{z} | {r:.3f} | {f:.2f} | {h:.0f} |" for s, j, d, z, r, f, h in rows]
    lines += ["", f"Mean over seeds: detection {det:.3f} (pass if >= {DETECT_MIN}): **{'PASS' if pass_a else 'FAIL'}**; "
              f"voted window FP/h {fph:.2f} (pass if within {FPH_RANGE}): **{'PASS' if pass_b else 'FAIL'}**.",
              "", f"Gate: **{'PASS' if pass_a and pass_b else 'FAIL'}**. EpiDeNet: 165/181 detected (0.912), 2.24 FP/h with its vote."]
    out = os.path.join(args.runs, "sanity_gate.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
