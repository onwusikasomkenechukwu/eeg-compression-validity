"""One fold: train FP32, quantize, threshold, smooth, score with SzCORE.

Fold k tests on folds[k], validates on folds[k+1] (which choose the early-stopping epoch and
the thresholds) and trains on the rest; no window sits in two of these sets. Patient-specific
arm: folds are one patient's records (records.make_folds). Cross-patient arm: folds are patient
groups (records.cross_patient_folds). Post-training quantization reuses the fold's FP32
weights, so every comparison is paired. The model (models.SPECS) fixes the window length,
input rate, channels and training settings; the dataset module supplies the records.

Choices not fixed by the plan or EpiDeNet, to be stated in the pre-registration:
  - Training windows: seizure windows (at least half seizure) every 1 s; background
    windows (no seizure) on the model's window grid, sampled at BG_PER_SZ per seizure
    window. Windows that are partly seizure but under half are left out of training.
  - Class-weighted cross-entropy (EpiDeNet's SSWCE loss was tuned on PEDESITE, not CHB-MIT).
  - EpiDeNet: Adam, lr 1e-3, batch 256, at most 300 epochs, early stopping after 10 epochs
    without validation-loss improvement (validation loss on the window grid); the best
    epoch's weights are kept. (A 100-epoch cap was hit with validation loss still
    falling on chb01.) Ahlawat's model: his settings (models.py).
  - Per-channel standardization from training-window statistics.
  - Quantization-aware training: fine-tunes the fold's FP32 model at 8 bits on the same
    training windows (Adam, lr 1e-4, at most 30 epochs, early stopping after 5 epochs
    without validation-loss improvement), then thresholded and scored like every model.
    Compared only against the FP32 seed band, not as a paired test.
  - Evaluation: the model's windows every 1 s, so latency resolves to 1 s.
  - Threshold: per model, the TARGET_SPEC quantile of its scores on the validation
    records' seizure-free windows (the plan's specificity-matched operating point); a
    window is positive only when its score is strictly above it (alarm_raw: ties matter
    for quantized models' coarse scores).
    Reusing the FP32 threshold on quantized models is the secondary, calibration result.
  - Tolerance band: per patient and seed, FP32 test window specificity pooled over all
    the patient's held-out hours must land within SPEC_TOLERANCE of TARGET_SPEC (checked
    in scripts/analyze_frontier.py, matching how false alarms are pooled). Out-of-band
    results are reported, never re-thresholded on test data. Each fold's own value is kept
    as a diagnostic (spec_in_band): a single ~6 h test fold misses the band more often,
    because artifacts cluster within records (7/21 folds on chb01, all below).
  - Smoothing (the frontier's knob): an alarm is on at decision time t when more than
    half of the windows ending in the last W seconds are positive. W = 12 s is the
    default, the 1 s-hop analogue of EpiDeNet's three-window majority vote; the sweep
    goes up from there (SMOOTH_GRID also keeps 4 and 8 s for context). Causal: it
    never looks ahead.
  - Alarm time: a window's decision is available at its end, so an alarm raised on the
    window [s, s+W) is timed at s+W. Latency is measured from that time.
  - EpiDeNet-comparable metrics (for the FP32 sanity gate): window-level false positives
    per hour on the non-overlapping window grid, raw and with EpiDeNet's causal 2-of-3
    vote, and seizures with at least one positive (voted) window inside the seizure.
"""
import time

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import average_precision_score, roc_auc_score

from devices import describe, get_device
from models import SPECS
from quantize import QAT, FakeQuant, Float16Sim, OnnxInt8
from records import FS, seizure_fraction, window_starts
from scoring import score_record

BG_PER_SZ = 10
TARGET_SPEC = 0.995
SPEC_TOLERANCE = 0.005  # test specificity must land in [0.990, 1.000]
BATCH = 256
QAT_LR, QAT_MAX_EPOCHS, QAT_PATIENCE = 1e-4, 30, 5  # fine-tuning from the FP32 weights
SMOOTH_GRID = [4, 8, 12, 16, 20, 24, 30, 36, 45, 60, 75, 90, 120]  # seconds
DEFAULT_SMOOTH = 12
VARIANTS = ["fp32", "int8", "sim8", "sim6", "sim4", "qat8"]


class Geometry:
    """A model's input geometry: sampling rate, window, 1 s hop, window grid, tensor layout."""

    def __init__(self, spec):
        self.decim = spec.decim
        self.fs = FS // spec.decim
        self.win = spec.win_s * self.fs
        self.hop = self.fs                 # evaluate every 1 s
        self.grid = self.win // self.hop   # every grid-th 1 s-hop window is non-overlapping
        self.layout = spec.layout


EPIDENET = Geometry(SPECS["epidenet"])


def _windows(x, starts, g):
    if len(starts):
        return np.stack([x[:, s:s + g.win] for s in starts])
    return np.zeros((0, x.shape[0], g.win), np.float16)


def eval_windows(rec, g=EPIDENET, hop=None):
    """The model's windows of a record every `hop` samples (default 1 s), with labels (at
    least half seizure)."""
    x, events, _ = rec
    starts = window_starts(x.shape[1], g.win, hop or g.hop)
    frac = seizure_fraction(starts, g.win, events, x.shape[1], g.fs)
    return _windows(x, starts, g), (frac >= 0.5).astype(np.int64)


def train_windows(recs, rng, g=EPIDENET):
    xs_sz, xs_bg = [], []
    for x, events, _ in recs:
        n = x.shape[1]
        s_sz = window_starts(n, g.win, g.hop)
        s_sz = s_sz[seizure_fraction(s_sz, g.win, events, n, g.fs) >= 0.5]
        s_bg = window_starts(n, g.win, g.win)
        s_bg = s_bg[seizure_fraction(s_bg, g.win, events, n, g.fs) == 0]
        xs_sz.append(_windows(x, s_sz, g))
        xs_bg.append((x, s_bg))
    x_sz = np.concatenate(xs_sz)
    # Sample background windows across all records, without replacement.
    pool = [(i, s) for i, (_, ss) in enumerate(xs_bg) for s in ss]
    take = rng.choice(len(pool), size=min(len(pool), BG_PER_SZ * len(x_sz)), replace=False)
    x_bg = np.stack([xs_bg[pool[j][0]][0][:, pool[j][1]:pool[j][1] + g.win] for j in take])
    X = np.concatenate([x_sz, x_bg])
    y = np.concatenate([np.ones(len(x_sz), np.int64), np.zeros(len(x_bg), np.int64)])
    return X, y


def _to_tensor(X, mean, std, g=EPIDENET):
    Z = (X.astype(np.float32) - mean) / std
    return torch.from_numpy(Z[:, None] if g.layout == "2d" else Z)


@torch.no_grad()
def predict(fn, X, mean, std, g=EPIDENET, batch=2048):
    """Seizure probability per window on the CPU; fn maps a normalized tensor to logits."""
    out = []
    for i in range(0, len(X), batch):
        logits = fn(_to_tensor(X[i:i + batch], mean, std, g))
        out.append(torch.softmax(logits.float(), 1)[:, 1])
    return torch.cat(out).numpy() if out else np.zeros(0)


def alarm_raw(scores, thr):
    """A window is positive only when its score is strictly above the threshold. Quantized
    models output few distinct scores (INT8 EpiDeNet/Ahlawat: about 130), so many validation
    windows can sit exactly on the threshold quantile; '>' keeps validation specificity at or
    above the target however coarse the scores are ('>=' let a collapsed 4-bit model's ties
    turn 0.995 into 0.10)."""
    return scores > thr


def smooth_votes(pred, k=3, need=2):
    """Causal vote on consecutive windows: positive at t when at least `need` of the last `k` are."""
    c = np.convolve(pred.astype(int), np.ones(k, int))[:len(pred)]
    return c >= need


def smooth_seconds(pred, w_s, hop_s=1.0):
    """Causal majority over the windows ending in the last w_s seconds (1 s hop)."""
    k = max(1, int(round(w_s / hop_s)))
    c = np.convolve(pred.astype(int), np.ones(k, int))[:len(pred)]
    n = np.minimum(np.arange(1, len(pred) + 1), k)
    return c * 2 > n


def to_events(alarm, duration, g=EPIDENET):
    """Alarmed decisions -> [(start_s, end_s)]. Decision i is made at the end of its window,
    (i * hop + win) / fs, and holds for one hop; contiguous decisions merge."""
    events, i = [], 0
    while i < len(alarm):
        if alarm[i]:
            j = i
            while j + 1 < len(alarm) and alarm[j + 1]:
                j += 1
            start = (i * g.hop + g.win) / g.fs
            events.append((start, min((j * g.hop + g.win + g.hop) / g.fs, duration)))
            i = j + 1
        else:
            i += 1
    return [e for e in events if e[1] > e[0]]


def frontier_rows(test, scores, thr, variant, thr_mode, g=EPIDENET):
    """SzCORE scores at every smoothing width for one model and threshold on the test records."""
    rows = []
    for w in SMOOTH_GRID:
        tp = fp = ref = 0
        hours, lats = 0.0, []
        for (path, rec), sc in zip(test, scores):
            s, lat = score_record(rec[1], to_events(smooth_seconds(alarm_raw(sc, thr), w), rec[2], g), rec[2])
            tp, fp, ref = tp + s.tp, fp + s.fp, ref + s.refTrue
            hours += rec[2] / 3600
            lats += lat
        rows.append({"variant": variant, "thr_mode": thr_mode, "smooth_s": w, "tp": tp, "fp": fp,
                     "seizures": ref, "hours": hours, "latencies_s": lats})
    return rows


def epidenet_metrics(test, scores, labels, thr, g=EPIDENET):
    """Window-level metrics on the non-overlapping window grid, as EpiDeNet reports them."""
    fp_raw = fp_vote = neg = pos = tp_raw = tp_vote = 0
    detected = seizures = 0
    hours = 0.0
    for (path, rec), sc, y in zip(test, scores, labels):
        p, yy = alarm_raw(sc[::g.grid], thr), y[::g.grid]
        v = smooth_votes(p)
        fp_raw += int((p & (yy == 0)).sum())
        fp_vote += int((v & (yy == 0)).sum())
        tp_raw += int((p & (yy == 1)).sum())
        tp_vote += int((v & (yy == 1)).sum())
        neg += int((yy == 0).sum())
        pos += int((yy == 1).sum())
        hours += rec[2] / 3600
        starts = np.arange(len(yy)) * g.win
        for ev in rec[1]:
            seizures += 1
            inside = seizure_fraction(starts, g.win, [ev], rec[0].shape[1], g.fs) >= 0.5
            detected += int((v & inside).any())
    return {"fp_per_h_raw": fp_raw / hours, "fp_per_h_vote": fp_vote / hours,
            "sens_raw": tp_raw / max(pos, 1), "sens_vote": tp_vote / max(pos, 1),
            "spec_raw": 1 - fp_raw / max(neg, 1), "spec_vote": 1 - fp_vote / max(neg, 1),
            "seizures_detected": detected, "seizures": seizures, "hours": hours}


def train_fp32(X, y, Xv, yv, mean, std, seed, device_name, log, spec=SPECS["epidenet"], g=EPIDENET,
               class_weight="inverse"):
    torch.manual_seed(seed)  # initialization is drawn on the CPU, so it is the same on every device
    model = spec.make(X.shape[1])
    return fit(model, X, y, Xv, yv, mean, std, seed, device_name, log, spec.lr, spec.max_epochs, spec.patience, g,
               class_weight)


def fit(model, X, y, Xv, yv, mean, std, seed, device_name, log, lr, max_epochs, patience, g=EPIDENET,
        class_weight="inverse"):
    """Training with early stopping on validation loss; returns the best epoch's model on the
    CPU, in eval mode. Shared by FP32 training and QAT fine-tuning. class_weight "inverse"
    (every registered run) weights the seizure class by the background:seizure ratio of the
    training windows; "none" is plain cross-entropy (the exploratory unweighted-loss check)."""
    if class_weight not in ("inverse", "none"):
        raise ValueError(f"class_weight must be 'inverse' or 'none', not {class_weight!r}")
    device = get_device(device_name)
    if device.type == "cuda":  # repeatable runs on NVIDIA GPUs (at a small speed cost)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    model = model.to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    w = (torch.tensor([1.0, (y == 0).sum() / max((y == 1).sum(), 1)], dtype=torch.float32).to(device)
         if class_weight == "inverse" else None)
    loss_fn = nn.CrossEntropyLoss(weight=w)
    Xt, yt = _to_tensor(X, mean, std, g).to(device), torch.from_numpy(y).to(device)
    Xvt, yvt = _to_tensor(Xv, mean, std, g).to(device), torch.from_numpy(yv).to(device)
    gen = torch.Generator().manual_seed(seed)

    best, best_state, bad, epoch_times = np.inf, None, 0, []
    for epoch in range(max_epochs):
        te = time.perf_counter()
        model.train()
        perm = torch.randperm(len(yt), generator=gen).to(device)
        for i in range(0, len(perm), BATCH):
            idx = perm[i:i + BATCH]
            opt.zero_grad()
            loss_fn(model(Xt[idx]), yt[idx]).backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            vl = sum(loss_fn(model(Xvt[i:i + 4096]), yvt[i:i + 4096]).item() * len(yvt[i:i + 4096])
                     for i in range(0, len(yvt), 4096)) / len(yvt)
        epoch_times.append(time.perf_counter() - te)
        if vl < best - 1e-4:
            best, bad = vl, 0
            best_state = {n: v.detach().cpu().clone() for n, v in model.state_dict().items()}
        else:
            bad += 1
        if epoch % 10 == 0 or bad >= patience:
            log(f"  epoch {epoch + 1}: val loss {vl:.4f} (best {best:.4f}, {epoch_times[-1]:.1f} s)")
        if bad >= patience:
            break
    model.load_state_dict(best_state)
    model = model.cpu().eval()
    return model, {"epochs": len(epoch_times), "s_per_epoch": float(np.mean(epoch_times)),
                   "stopped_early": bad >= patience, "best_val_loss": best}


def run_fold(folds, k, cache_root, ds, model="epidenet", seed=0, threads=4, device="cpu", log=print):
    """Train FP32 on fold k, quantize it, and evaluate every model. ds is a dataset module
    (chbmit, siena, seizeit2). Returns (summary, arrays): summary is JSON-serializable; arrays
    holds raw scores, trained weights and normalization for later analysis."""
    spec = SPECS[model]
    g = Geometry(spec)
    channels = spec.channels[ds.NAME]
    torch.set_num_threads(threads)
    rng = np.random.default_rng(seed)
    t = {}

    t0 = time.perf_counter()
    nk = (k + 1) % len(folds)
    test_paths, val_paths = folds[k], folds[nk]
    train_paths = [p for i, f in enumerate(folds) if i not in (k, nk) for p in f]

    def load(paths):
        out = []
        for p in paths:
            x, events, dur = ds.load_record(p, cache_root, channels)
            if x is not None:
                out.append((p, (x[:, ::g.decim] if g.decim > 1 else x, events, dur)))
        return out

    test, val, train = load(test_paths), load(val_paths), load(train_paths)
    t["load_s"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    X, y = train_windows([r for _, r in train], rng, g)
    mean = X.astype(np.float32).mean(axis=(0, 2), keepdims=True)[0]
    std = X.astype(np.float32).std(axis=(0, 2), keepdims=True)[0] + 1e-6
    Xvg, yvg = map(np.concatenate, zip(*[eval_windows(r, g, hop=g.win) for _, r in val]))
    t["windows_s"] = time.perf_counter() - t0
    log(f"train windows {len(y)} ({y.sum()} seizure), val windows {len(yvg)} ({yvg.sum()} seizure, window grid)")

    t0 = time.perf_counter()
    model_fp32, tinfo = train_fp32(X, y, Xvg, yvg, mean, std, seed, device, log, spec, g)
    t.update(tinfo)
    t["train_s"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    calib_idx = rng.choice(len(X), size=min(2000, len(X)), replace=False)
    calib = _to_tensor(X[calib_idx], mean, std, g)
    onnx = OnnxInt8(model_fp32, calib, seed=seed)
    fns = {"fp32": model_fp32, "int8": onnx}
    for b in (8, 6, 4):
        fns[f"sim{b}"] = FakeQuant(model_fp32, b).calibrate(calib).eval()
    t["quantize_s"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    qat, qinfo = fit(QAT(model_fp32, 8).calibrate(calib), X, y, Xvg, yvg, mean, std, seed, device, log,
                     QAT_LR, QAT_MAX_EPOCHS, QAT_PATIENCE, g)
    fns["qat8"] = qat
    t["qat"] = qinfo
    t["qat_s"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    # Export check: ONNX FP32 must reproduce the PyTorch model.
    probe = calib[:512]
    with torch.no_grad():
        onnx_diff = float((model_fp32(probe) - onnx(probe, fp32=True)).abs().max())

    def score_records(recs):
        """1 s-hop windows of one record at a time, scored by every model, so a job never
        holds more than one record's windows in memory."""
        labels, sc = [], {n: [] for n in fns}
        for _, r in recs:
            Xr, yr = eval_windows(r, g)
            labels.append(yr)
            for n, fn in fns.items():
                sc[n].append(predict(fn, Xr, mean, std, g))
        return labels, sc

    val_labels, val_sc = score_records(val)
    yv = np.concatenate(val_labels)
    val_scores = {n: np.concatenate(v) for n, v in val_sc.items()}
    thr = {n: float(np.quantile(val_scores[n][yv == 0], TARGET_SPEC)) for n in fns}
    labels, test_scores = score_records(test)

    rows = []
    for name in fns:
        rows += frontier_rows(test, test_scores[name], thr[name], name, "own", g)
        if name != "fp32":
            rows += frontier_rows(test, test_scores[name], thr["fp32"], name, "fp32", g)

    y_all = np.concatenate(labels)
    window = {}
    for name in fns:
        p_all = np.concatenate(test_scores[name])
        spec_ = float(((~alarm_raw(p_all, thr[name])) & (y_all == 0)).sum() / max((y_all == 0).sum(), 1))
        window[name] = {
            "auroc": float(roc_auc_score(y_all, p_all)) if 0 < y_all.sum() < len(y_all) else None,
            "auprc": float(average_precision_score(y_all, p_all)) if y_all.sum() else None,
            "specificity": spec_,
            "epidenet": epidenet_metrics(test, test_scores[name], labels, thr[name], g),
        }
    t["eval_s"] = time.perf_counter() - t0

    summary = {
        "dataset": ds.NAME, "model": spec.name, "channels": channels,
        "fold": k, "seed": seed, "device": device, "environment": describe(device),
        "test_records": [p.replace("\\", "/").split("/")[-1] for p, _ in test],
        "val_records": len(val), "train_records": len(train),
        "train_windows": int(len(y)), "train_seizure_windows": int(y.sum()),
        "thresholds": thr,
        "spec_in_band": abs(window["fp32"]["specificity"] - TARGET_SPEC) <= SPEC_TOLERANCE,
        "onnx_fp32_max_abs_logit_diff": onnx_diff,
        "window": window,
        "frontier": rows,
        "timing": t,
    }
    # Flat arrays (no pickle): split test arrays back into records with test_lengths. The trained
    # FP32 weights and normalization let every quantized model be rebuilt without retraining
    # (load_fp32); the QAT state (weights and activation ranges) is saved alongside.
    arrays = {"test_lengths": np.array([len(lab) for lab in labels]), "test_labels": y_all,
              "val_labels": yv,
              **{f"test_{n}": np.concatenate(test_scores[n]).astype(np.float32) for n in fns},
              **{f"val_{n}": val_scores[n].astype(np.float32) for n in fns},
              "norm_mean": mean, "norm_std": std, "calib_idx": calib_idx,
              **{f"w_fp32__{n}": v.numpy() for n, v in model_fp32.state_dict().items()},
              **{f"w_qat8__{n}": v.numpy() for n, v in qat.state_dict().items()}}
    return summary, arrays


ES_FRACTION = 0.25  # reimplementation check: share of training windows held out for early stopping


def stratified_holdout(y, frac, rng):
    """Boolean mask of a random `frac` of each class (rounded), drawn with rng."""
    held = np.zeros(len(y), bool)
    for c in np.unique(y):
        idx = np.flatnonzero(y == c)
        held[rng.choice(idx, size=int(round(frac * len(idx))), replace=False)] = True
    return held


LOSSES = {"weighted": "inverse", "unweighted": "none"}  # reimplementation check: loss -> fit's class_weight


def run_reimplementation_check(folds, k, cache_root, ds, model="epidenet", seed=0, threads=4, device="cpu",
                               log=print, loss="weighted"):
    """The protocol-matched reimplementation check (prereg/FIDELITY_UPDATE.md), FP32 only.
    EpiDeNet's protocol: folds are one seizure record each (records.loocv_seizure_folds);
    train on every other fold, test on fold k, positive window = the model's predicted class
    (probability > 0.5, the default decision), EpiDeNet's 2-of-3 vote. No validation fold:
    early stopping uses a stratified random ES_FRACTION of the training windows, held out
    from the gradient updates. Training windows, preprocessing and training settings are
    Stage 0's. Returns (summary, arrays) like run_fold; the summary keeps run_fold's
    window["fp32"]["epidenet"] layout, so scripts/sanity_gate.py reads it unchanged.
    loss "weighted" is the registered check; "unweighted" (plain cross-entropy) is the
    exploratory post hoc test of whether class weighting explains its failure."""
    class_weight = LOSSES[loss]
    spec = SPECS[model]
    g = Geometry(spec)
    channels = spec.channels[ds.NAME]
    torch.set_num_threads(threads)
    rng = np.random.default_rng(seed)
    t = {}

    t0 = time.perf_counter()
    test_paths = folds[k]
    train_paths = [p for i, f in enumerate(folds) if i != k for p in f]

    def load(paths):
        out = []
        for p in paths:
            x, events, dur = ds.load_record(p, cache_root, channels)
            if x is not None:
                out.append((p, (x[:, ::g.decim] if g.decim > 1 else x, events, dur)))
        return out

    test, train = load(test_paths), load(train_paths)
    t["load_s"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    X_all, y_all = train_windows([r for _, r in train], rng, g)
    held = stratified_holdout(y_all, ES_FRACTION, rng)
    X, y, Xes, yes = X_all[~held], y_all[~held], X_all[held], y_all[held]
    mean = X.astype(np.float32).mean(axis=(0, 2), keepdims=True)[0]
    std = X.astype(np.float32).std(axis=(0, 2), keepdims=True)[0] + 1e-6
    t["windows_s"] = time.perf_counter() - t0
    log(f"train windows {len(y)} ({y.sum()} seizure), early-stopping windows {len(yes)} ({yes.sum()} seizure)")

    t0 = time.perf_counter()
    model_fp32, tinfo = train_fp32(X, y, Xes, yes, mean, std, seed, device, log, spec, g, class_weight)
    t.update(tinfo)
    t["train_s"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    labels, scores = [], []
    for _, r in test:
        Xr, yr = eval_windows(r, g)
        labels.append(yr)
        scores.append(predict(model_fp32, Xr, mean, std, g))
    thr = 0.5  # default decision: argmax of the two classes (ties go to class 0, as alarm_raw's '>')
    y_test, p_test = np.concatenate(labels), np.concatenate(scores)
    window = {"fp32": {
        "auroc": float(roc_auc_score(y_test, p_test)) if 0 < y_test.sum() < len(y_test) else None,
        "specificity": float(((~alarm_raw(p_test, thr)) & (y_test == 0)).sum() / max((y_test == 0).sum(), 1)),
        "epidenet": epidenet_metrics(test, scores, labels, thr, g),
    }}
    t["eval_s"] = time.perf_counter() - t0

    summary = {
        "protocol": "epidenet", "loss": loss, "dataset": ds.NAME, "model": spec.name, "channels": channels,
        "fold": k, "seed": seed, "device": device, "environment": describe(device),
        "test_records": [p.replace("\\", "/").split("/")[-1] for p, _ in test],
        "train_records": len(train), "es_fraction": ES_FRACTION,
        "train_windows": int(len(y)), "train_seizure_windows": int(y.sum()),
        "es_windows": int(len(yes)), "es_seizure_windows": int(yes.sum()),
        "thresholds": {"fp32": thr},
        "window": window,
        "timing": t,
    }
    arrays = {"test_lengths": np.array([len(lab) for lab in labels]), "test_labels": y_test,
              "test_fp32": p_test.astype(np.float32), "norm_mean": mean, "norm_std": std,
              **{f"w_fp32__{n}": v.numpy() for n, v in model_fp32.state_dict().items()}}
    return summary, arrays


def load_fp32(arrays, model="epidenet"):
    """Rebuild a job's trained FP32 model and normalization from its saved .npz arrays.
    Returns (model, mean, std); quantized models follow from it (OnnxInt8, FakeQuant, ...)."""
    prefix = "w_fp32__"
    state = {k[len(prefix):]: torch.from_numpy(np.array(arrays[k])) for k in arrays.files if k.startswith(prefix)}
    mean, std = np.array(arrays["norm_mean"]), np.array(arrays["norm_std"])
    net = SPECS[model].make(mean.shape[0])
    net.load_state_dict(state)
    return net.eval(), mean, std


# Exploratory bit widths added after registration (Aryal, 2026-11-10: map bit widths to hardware).
EXTRA_VARIANTS = {
    "w4a8": lambda net, calib: FakeQuant(net, 4, act_bits=8).calibrate(calib).eval(),
    "fp16": lambda net, calib: Float16Sim(net).eval(),
}


def rescore_fold(folds, k, cache_root, ds, arrays, variants=("w4a8", "fp16"), model="epidenet", seed=0,
                 threads=4, log=print):
    """Rebuild a finished run_fold job's FP32 model from its saved arrays, derive further
    post-training variants (EXTRA_VARIANTS) and evaluate them exactly as run_fold evaluates
    its quantized models: thresholds at TARGET_SPEC on the validation fold's seizure-free
    windows, frontier rows with their own and with FP32's threshold, window metrics. No
    training. The training windows are regenerated with the job's seed (calibration draws
    from them); the regenerated normalization and the rebuilt FP32 model's test scores are
    checked against the saved ones and reported."""
    spec = SPECS[model]
    g = Geometry(spec)
    channels = spec.channels[ds.NAME]
    torch.set_num_threads(threads)
    rng = np.random.default_rng(seed)
    t0 = time.perf_counter()

    nk = (k + 1) % len(folds)
    train_paths = [p for i, f in enumerate(folds) if i not in (k, nk) for p in f]

    def load(paths):
        out = []
        for p in paths:
            x, events, dur = ds.load_record(p, cache_root, channels)
            if x is not None:
                out.append((p, (x[:, ::g.decim] if g.decim > 1 else x, events, dur)))
        return out

    test, val, train = load(folds[k]), load(folds[nk]), load(train_paths)
    X, _ = train_windows([r for _, r in train], rng, g)
    net, mean, std = load_fp32(arrays, model)
    mean_regen = X.astype(np.float32).mean(axis=(0, 2), keepdims=True)[0]
    checks = {"norm_mean_max_abs_diff": float(np.abs(mean_regen - mean).max())}
    calib = _to_tensor(X[np.array(arrays["calib_idx"])], mean, std, g)
    fns = {"fp32": net, **{v: EXTRA_VARIANTS[v](net, calib) for v in variants}}

    def score_records(recs):
        labels, sc = [], {n: [] for n in fns}
        for _, r in recs:
            Xr, yr = eval_windows(r, g)
            labels.append(yr)
            for n, fn in fns.items():
                sc[n].append(predict(fn, Xr, mean, std, g))
        return labels, sc

    val_labels, val_sc = score_records(val)
    yv = np.concatenate(val_labels)
    val_scores = {n: np.concatenate(v) for n, v in val_sc.items()}
    thr = {n: float(np.quantile(val_scores[n][yv == 0], TARGET_SPEC)) for n in fns}
    labels, test_scores = score_records(test)
    checks["test_fp32_max_abs_diff"] = float(np.abs(np.concatenate(test_scores["fp32"])
                                                    - np.array(arrays["test_fp32"])).max())
    log(f"checks: {checks}")

    rows = []
    for name in variants:
        rows += frontier_rows(test, test_scores[name], thr[name], name, "own", g)
        rows += frontier_rows(test, test_scores[name], thr["fp32"], name, "fp32", g)
    y_all = np.concatenate(labels)
    window = {}
    for name in variants:
        p_all = np.concatenate(test_scores[name])
        window[name] = {
            "auroc": float(roc_auc_score(y_all, p_all)) if 0 < y_all.sum() < len(y_all) else None,
            "specificity": float(((~alarm_raw(p_all, thr[name])) & (y_all == 0)).sum() / max((y_all == 0).sum(), 1)),
            "epidenet": epidenet_metrics(test, test_scores[name], labels, thr[name], g),
        }
    summary = {"variants": list(variants), "fold": k, "seed": seed, "thresholds": thr, "checks": checks,
               "window": window, "frontier": rows, "timing": {"total_s": time.perf_counter() - t0}}
    arrays_out = {f"test_{n}": np.concatenate(test_scores[n]).astype(np.float32) for n in variants}
    return summary, arrays_out
