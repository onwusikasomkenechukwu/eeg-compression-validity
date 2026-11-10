"""Run (fold, seed) jobs: train FP32, quantize, score. Any dataset, model and arm.

  --dataset chbmit | siena | seizeit2      (data under data/<dataset> unless --data-root)
  --model   epidenet | ahlawat             (models.SPECS; ahlawat needs chbmit's 18 channels)
  --arm     patient (patient-specific folds, one unit per patient)
            cross   (leave one patient group out; a single unit "xpat")
  --protocol plan     (the registered design: run_fold, FP32 + quantized models)
             epidenet (the reimplementation check, prereg/FIDELITY_UPDATE.md: EpiDeNet's
                       leave-one-seizure-record-out, FP32 only; patient arm only)

Each job writes
  <out>/<unit>/fold<k>_seed<s>.json   summary, frontier rows, thresholds, timing, environment
  <out>/<unit>/fold<k>_seed<s>.npz    raw scores; trained FP32 weights and normalization; QAT state
  <out>/<unit>/fold<k>_seed<s>.log    training log, then "ok" or the traceback
In the cross arm each fold's summary carries its test group as "patient", so the analysis
reads every arm the same way.

Resumable: a job whose JSON exists is skipped. Jobs are claimed with an exclusive
<stem>.claim file, so several runners (CPU and GPU, or several machines sharing the output
folder) never run the same job. A runner killed mid-job leaves its claim behind; restart with
--clear-claims once no other runner is active.

Threads are pinned at 4 per job (the default): the thread count changes results slightly, so
keep it fixed for a whole run. Memory: signals are memory-mapped from the cache, so a job holds
its training windows plus one record's evaluation windows at a time.

Usage:
  # Stage 0 (pinned): CHB-MIT, EpiDeNet, patient-specific, WSL, CPU only
  python scripts/run_patient.py --patients all --seeds 0 1 2 --workers 2 --threads 4
  # Stage 1: 5 seeds; Ahlawat's model; the cross-patient arm (cluster-sized)
  python scripts/run_patient.py --patients all --seeds 0 1 2 3 4 --out runs/stage1
  python scripts/run_patient.py --model ahlawat --patients all --seeds 0 1 2 --out runs/stage1_ahlawat
  python scripts/run_patient.py --arm cross --seeds 0 1 2 --out runs/stage1_cross
  # Reimplementation check (FP32 only, EpiDeNet's protocol); then scripts/sanity_gate.py --protocol epidenet
  python scripts/run_patient.py --protocol epidenet --patients all --seeds 0 1 2 --workers 2 --threads 4 --out runs/gate_check
  # Stage 2 / 3: Siena and SeizeIT2 (patients with at least 3 seizure records)
  python scripts/run_patient.py --dataset siena --patients all --out runs/stage2_siena
  python scripts/run_patient.py --dataset seizeit2 --patients all --out runs/stage3_seizeit2
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

_DEVICE = "cpu"


def _init_worker(devices):
    global _DEVICE
    _DEVICE = devices.get()


def build_folds(ds, data_root, arm, unit, channels, protocol="plan"):
    from records import cross_patient_folds, loocv_seizure_folds, make_folds
    if arm == "cross":
        return cross_patient_folds(ds, data_root, channels)
    make = loocv_seizure_folds if protocol == "epidenet" else make_folds
    return make(ds.usable_records(data_root, unit, channels)), None


def _job(args):
    dataset, model, arm, protocol, unit, k, seed, data_root, cache, out_dir, threads = args
    import numpy as np
    from models import SPECS
    from pipeline import run_fold, run_reimplementation_check

    ds = importlib.import_module(dataset)
    stem = os.path.join(out_dir, unit, f"fold{k}_seed{seed}")
    try:
        fd = os.open(stem + ".claim", os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, f"{os.getpid()} {_DEVICE} {time.ctime()}".encode())
        os.close(fd)
    except FileExistsError:
        return unit, k, seed, _DEVICE, "skipped (claimed by another runner)", 0.0
    if os.path.exists(stem + ".json"):  # finished by another runner after we listed it
        os.remove(stem + ".claim")
        return unit, k, seed, _DEVICE, "skipped (done)", 0.0

    log_lines = []
    status = "FAILED"
    t0 = time.perf_counter()
    try:
        folds, names = build_folds(ds, data_root, arm, unit, SPECS[model].channels[dataset], protocol)
        run = run_reimplementation_check if protocol == "epidenet" else run_fold
        summary, arrays = run(folds, k, cache, ds, model=model, seed=seed, threads=threads,
                              device=_DEVICE, log=log_lines.append)
        summary["patient"] = names[k] if arm == "cross" else unit
        summary["arm"] = arm
        summary["timing"]["total_s"] = time.perf_counter() - t0
        np.savez_compressed(stem + ".npz", **arrays)
        with open(stem + ".json.tmp", "w") as f:
            json.dump(summary, f)
        os.replace(stem + ".json.tmp", stem + ".json")  # the JSON marks the job done
        status = "ok"
    except Exception:
        status = "FAILED\n" + traceback.format_exc()
    finally:
        with open(stem + ".log", "w") as f:
            f.write("\n".join(log_lines + [status]))
        os.remove(stem + ".claim")
    return unit, k, seed, _DEVICE, status, time.perf_counter() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="chbmit", choices=["chbmit", "siena", "seizeit2"])
    ap.add_argument("--model", default="epidenet", choices=["epidenet", "ahlawat"])
    ap.add_argument("--arm", default="patient", choices=["patient", "cross"])
    ap.add_argument("--protocol", default="plan", choices=["plan", "epidenet"],
                    help="epidenet: the FP32 reimplementation check (patient arm only)")
    ap.add_argument("--patients", nargs="+", default=["chb01"],
                    help="patient ids, or 'all' (patient arm; ignored by the cross arm)")
    ap.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    ap.add_argument("--folds", nargs="*", type=int, default=None, help="default: every fold")
    ap.add_argument("--workers", type=int, default=2, help="parallel CPU jobs")
    ap.add_argument("--threads", type=int, default=4,
                    help="CPU threads per job; changes results slightly, so keep it fixed for a whole run "
                         "(Stage 0 and the chb01 pilot: 4)")
    ap.add_argument("--gpu-workers", type=int, default=0, help="parallel jobs that train on --gpu-device")
    ap.add_argument("--gpu-device", default="cuda", choices=["cuda", "dml"])
    ap.add_argument("--data-root", default=None, help="default: data/<dataset>")
    ap.add_argument("--cache", default=os.path.expanduser(os.path.join("~", "eegcv_cache")),
                    help="preprocessed-signal cache root; keep it on a local disk")
    ap.add_argument("--out", default=None, help="default: runs/stage0 (plan) or runs/gate_check (epidenet)")
    ap.add_argument("--clear-claims", action="store_true",
                    help="delete leftover .claim files first (only when no other runner is active)")
    args = ap.parse_args()
    if args.protocol == "epidenet" and args.arm != "patient":
        sys.exit("--protocol epidenet runs on the patient arm only")
    # Separate folders: the two protocols share job names, and a finished job is skipped.
    args.out = args.out or os.path.join(ROOT, "runs", "gate_check" if args.protocol == "epidenet" else "stage0")

    from models import SPECS
    ds = importlib.import_module(args.dataset)
    data_root = args.data_root or os.path.join(ROOT, "data", args.dataset)
    channels = SPECS[args.model].channels.get(args.dataset)
    if channels is None:
        sys.exit(f"model {args.model} has no channel set for {args.dataset}")

    if args.clear_claims:
        stale = glob.glob(os.path.join(args.out, "*", "*.claim"))
        for c in stale:
            os.remove(c)
        print(f"cleared {len(stale)} claim file(s)", flush=True)

    if args.arm == "cross":
        units = ["xpat"]
        to_cache = [p for pat in ds.list_patients(data_root) for p, _ in ds.usable_records(data_root, pat, channels)]
    else:
        units = ds.list_patients(data_root) if args.patients == ["all"] else args.patients
        to_cache = None

    jobs = []
    for unit in units:
        try:
            folds, names = build_folds(ds, data_root, args.arm, unit, channels, args.protocol)
        except ValueError as e:  # too few seizure records
            print(f"{unit}: skipped ({e})", flush=True)
            continue
        os.makedirs(os.path.join(args.out, unit), exist_ok=True)
        # Cache every record once here, so parallel workers never race to write the cache.
        t0 = time.perf_counter()
        recs = to_cache if to_cache is not None else [p for f in folds for p in f]
        for p in recs:
            ds.load_record(p, args.cache, channels)
        print(f"{unit}: {len(recs)} records, {len(folds)} folds"
              + (f" (test groups: {', '.join(names)})" if names else "")
              + f", cached in {time.perf_counter() - t0:.0f} s", flush=True)
        for k in (args.folds if args.folds is not None else range(len(folds))):
            for s in args.seeds:
                stem = os.path.join(args.out, unit, f"fold{k}_seed{s}")
                if not os.path.exists(stem + ".json") and not os.path.exists(stem + ".claim"):
                    jobs.append((args.dataset, args.model, args.arm, args.protocol, unit, k, s, data_root, args.cache,
                                 args.out, args.threads))

    n_proc = args.workers + args.gpu_workers
    print(f"{len(jobs)} jobs ({args.dataset}, {args.model}, {args.arm} arm, {args.protocol} protocol) on {args.workers} CPU worker(s) + "
          f"{args.gpu_workers} {args.gpu_device} worker(s), {args.threads} thread(s) each", flush=True)
    if not jobs:
        return
    ctx = mp.get_context("spawn")
    devices = ctx.Queue()
    for _ in range(args.gpu_workers):
        devices.put(args.gpu_device)
    for _ in range(args.workers):
        devices.put("cpu")
    t0 = time.perf_counter()
    with ctx.Pool(n_proc, initializer=_init_worker, initargs=(devices,)) as pool:
        for i, (unit, k, s, dev, status, dt) in enumerate(pool.imap_unordered(_job, jobs), 1):
            print(f"[{i}/{len(jobs)}] {unit} fold {k} seed {s} ({dev}): {status.splitlines()[0]} in {dt:.0f} s "
                  f"(elapsed {(time.perf_counter() - t0) / 60:.1f} min)", flush=True)
            if status.startswith("FAILED"):
                print(status, flush=True)


if __name__ == "__main__":
    main()
