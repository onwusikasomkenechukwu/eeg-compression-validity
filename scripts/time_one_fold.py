"""Week-1 measurement: train and score one patient-specific EpiDeNet fold, timed.

Usage (inside WSL):
  python scripts/time_one_fold.py --patient chb01 --fold 0 --seed 0
Writes runs/time_one_fold/<patient>_fold<k>_seed<s>.json.
"""
import argparse
import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import chbmit  # noqa: E402
from chbmit import make_folds, usable_records  # noqa: E402
from pipeline import DEFAULT_SMOOTH, SPEC_TOLERANCE, TARGET_SPEC, run_fold  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--patient", default="chb01")
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--data-root", default=os.path.join(ROOT, "data", "chbmit"))
    # Cache on the Linux filesystem: reading from /mnt/c is slow under WSL.
    ap.add_argument("--cache", default=os.path.expanduser("~/eegcv_cache"))
    args = ap.parse_args()

    t0 = time.perf_counter()
    recs = usable_records(args.data_root, args.patient)
    folds = make_folds(recs)
    print(f"{args.patient}: {len(recs)} records, {sum(h for _, h in recs)} with seizures -> {len(folds)} folds; "
          f"fold {args.fold} tests on {[os.path.basename(p) for p in folds[args.fold]]}", flush=True)

    res, _ = run_fold(folds, args.fold, args.cache, chbmit,
                      seed=args.seed, threads=args.threads, log=lambda m: print(m, flush=True))
    res["patient"] = args.patient
    res["timing"]["total_s"] = time.perf_counter() - t0

    out_dir = os.path.join(ROOT, "runs", "time_one_fold")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"{args.patient}_fold{args.fold}_seed{args.seed}.json")
    with open(out, "w") as f:
        json.dump(res, f, indent=2)

    t, w = res["timing"], res["window"]["fp32"]
    op = next(r for r in res["frontier"] if r["variant"] == "fp32" and r["smooth_s"] == DEFAULT_SMOOTH)
    print(f"\nFP32 at {DEFAULT_SMOOTH} s smoothing: seizures detected {op['tp']}/{op['seizures']}, "
          f"false alarms {op['fp']} over {op['hours']:.1f} h, latencies {op['latencies_s']}")
    print(f"window AUROC {w['auroc']}, AUPRC {w['auprc']}, specificity {w['specificity']:.4f} "
          f"({'within' if res['spec_in_band'] else 'OUTSIDE'} target {TARGET_SPEC} +/- {SPEC_TOLERANCE})")
    print(f"timing: load {t['load_s']:.0f} s, windows {t['windows_s']:.0f} s, "
          f"train {t['train_s']:.0f} s ({t['epochs']} epochs, {t['s_per_epoch']:.1f} s/epoch, "
          f"{'early stop' if t['stopped_early'] else 'hit epoch cap'}), quantize {t['quantize_s']:.0f} s, "
          f"evaluate {t['eval_s']:.0f} s, total {t['total_s']:.0f} s")
    print(f"saved {out}")


if __name__ == "__main__":
    main()
