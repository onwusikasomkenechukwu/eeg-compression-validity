"""Exploratory, added after registration: W4A8 and FP16 versions of every Stage 0 model,
built from the saved FP32 weights (no training) and evaluated like Stage 0's quantized models
(pipeline.rescore_fold).

Each job writes <out>/<patient>/fold<k>_seed<s>.json: the Stage 0 job's frontier rows plus the
new variants' rows, so scripts/analyze_stats.py reads it like a Stage 0 run (--caps, or
--excess-only for the excess-latency table), and <stem>.npz with the new test scores.
Resumable: a job whose JSON exists is skipped.

Usage: python scripts/rescore_bitwidths.py --runs runs/stage0 --out runs/stage0_bitwidths --workers 2 --threads 4
"""
import argparse
import glob
import importlib
import json
import multiprocessing as mp
import os
import sys
import time
import traceback

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))


def _job(args):
    src_json, out_dir, data_root, cache, threads = args
    import numpy as np
    from models import SPECS
    from pipeline import rescore_fold
    from run_patient import build_folds

    s0 = json.load(open(src_json))
    patient, k, seed = s0["patient"], s0["fold"], s0["seed"]
    stem = os.path.join(out_dir, patient, f"fold{k}_seed{seed}")
    log_lines, status, t0 = [], "FAILED", time.perf_counter()
    try:
        ds = importlib.import_module(s0["dataset"])
        model = s0["model"]
        folds, _ = build_folds(ds, data_root, "patient", patient, SPECS[model].channels[s0["dataset"]])
        arrays = np.load(src_json[:-5] + ".npz")
        summary, arrays_out = rescore_fold(folds, k, cache, ds, arrays, model=model, seed=seed,
                                           threads=threads, log=log_lines.append)
        summary.update({"patient": patient, "dataset": s0["dataset"], "model": s0["model"],
                        "source": os.path.relpath(src_json, ROOT).replace("\\", "/")})
        summary["frontier"] = s0["frontier"] + summary["frontier"]
        summary["window"] = {**s0["window"], **summary["window"]}
        summary["thresholds"] = {**s0["thresholds"], **summary["thresholds"]}
        np.savez_compressed(stem + ".npz", **arrays_out)
        with open(stem + ".json.tmp", "w") as f:
            json.dump(summary, f)
        os.replace(stem + ".json.tmp", stem + ".json")
        status = "ok"
    except Exception:
        status = "FAILED\n" + traceback.format_exc()
    finally:
        with open(stem + ".log", "w") as f:
            f.write("\n".join(log_lines + [status]))
    return patient, k, seed, status, time.perf_counter() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=os.path.join(ROOT, "runs", "stage0"))
    ap.add_argument("--out", default=os.path.join(ROOT, "runs", "stage0_bitwidths"))
    ap.add_argument("--patients", nargs="+", default=["all"])
    ap.add_argument("--seeds", nargs="+", type=int, default=None)
    ap.add_argument("--folds", nargs="+", type=int, default=None)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--threads", type=int, default=4, help="keep at Stage 0's 4")
    ap.add_argument("--data-root", default=os.path.join(ROOT, "data", "chbmit"))
    ap.add_argument("--cache", default=os.path.expanduser(os.path.join("~", "eegcv_cache")))
    args = ap.parse_args()

    jobs = []
    for p in sorted(glob.glob(os.path.join(args.runs, "*", "fold*_seed*.json"))):
        s = json.load(open(p))
        if args.patients != ["all"] and s["patient"] not in args.patients:
            continue
        if (args.seeds is not None and s["seed"] not in args.seeds) or (args.folds is not None and s["fold"] not in args.folds):
            continue
        os.makedirs(os.path.join(args.out, s["patient"]), exist_ok=True)
        if not os.path.exists(os.path.join(args.out, s["patient"], f"fold{s['fold']}_seed{s['seed']}.json")):
            jobs.append((p, args.out, args.data_root, args.cache, args.threads))
    print(f"{len(jobs)} jobs on {args.workers} worker(s), {args.threads} thread(s) each", flush=True)
    if not jobs:
        return
    t0 = time.perf_counter()
    with mp.get_context("spawn").Pool(args.workers) as pool:
        for i, (patient, k, seed, status, dt) in enumerate(pool.imap_unordered(_job, jobs), 1):
            print(f"[{i}/{len(jobs)}] {patient} fold {k} seed {seed}: {status.splitlines()[0]} in {dt:.0f} s "
                  f"(elapsed {(time.perf_counter() - t0) / 60:.1f} min)", flush=True)
            if status.startswith("FAILED"):
                print(status, flush=True)


if __name__ == "__main__":
    main()
