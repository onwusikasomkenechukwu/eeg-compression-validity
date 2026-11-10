"""Dataset-independent pieces: the common sampling rate, causal filtering and resampling,
the signal cache, window labels and the fold designs.

Every dataset module (chbmit, siena, seizeit2) exposes the same interface:
  NAME, CHANNEL_SETS, list_patients(root), usable_records(root, patient, channels),
  seizures(record), load_record(record, cache_root, channels), patient_groups(root)
and returns signals at FS (256 Hz) as float16 microvolts.
"""
import os

import numpy as np
from scipy.signal import butter, sosfilt

FS = 256  # every dataset is brought to 256 Hz


def bandpass_causal(raw, fs_in):
    """Causal 0.5-40 Hz 4th-order Butterworth band-pass at the input rate, then decimation to FS
    (an integer factor; the 40 Hz low edge is the anti-aliasing filter). Causal, so filtering
    never looks ahead, which matters for latency."""
    sos = butter(4, [0.5, 40.0], btype="bandpass", fs=fs_in, output="sos")
    y = sosfilt(sos, raw, axis=1)
    factor = int(round(fs_in / FS))
    assert factor * FS == fs_in, f"cannot decimate {fs_in} Hz to {FS} Hz by an integer factor"
    return y[:, ::factor]


def cached(cache_root, dataset, patient, tag, name, compute):
    """Return the cached float16 signal (memory-mapped, read lazily), computing and saving it
    on first use. The tag names the preprocessing, so a change can never reuse an old cache."""
    if not cache_root:
        x = compute()
        return None if x is None else x.astype(np.float16)
    path = os.path.join(cache_root, dataset, patient, tag, f"{name}.npy")
    if not os.path.exists(path):
        x = compute()
        if x is None:
            return None
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp.npy"
        np.save(tmp, x.astype(np.float16))
        os.replace(tmp, path)
    return np.load(path, mmap_mode="r")


def window_starts(n_samples, win, stride):
    return np.arange(0, n_samples - win + 1, stride)


def seizure_fraction(starts, win, events, n_samples, fs=FS):
    """Fraction of each window [s, s+win) covered by annotated seizure (events in seconds)."""
    mask = np.zeros(n_samples + 1, dtype=np.int64)
    for on, off in events:
        mask[int(round(on * fs)):int(round(off * fs))] = 1
    cum = np.concatenate([[0], np.cumsum(mask)])
    return (cum[starts + win] - cum[starts]) / win


def make_folds(records):
    """The plan's patient-specific fold design: one fold per seizure record, with the
    seizure-free records dealt round-robin across the same folds. records: [(record,
    has_seizure)], normally from usable_records. Returns a list of folds, each a list of
    records. Needs at least 3 seizure records (test, validation and training folds)."""
    sz = [p for p, has in records if has]
    free = [p for p, has in records if not has]
    if len(sz) < 3:
        raise ValueError(f"need at least 3 seizure records for test/validation/training folds, got {len(sz)}")
    folds = [[p] for p in sz]
    for i, p in enumerate(free):
        folds[i % len(folds)].append(p)
    return folds


def loocv_seizure_folds(records):
    """EpiDeNet's own protocol (the reimplementation check): one fold per seizure record;
    a job tests on its fold and trains on all the others, so seizure-free records are
    never used. records: [(record, has_seizure)]. Returns a list of one-record folds.
    Needs at least 2 seizure records (one to test, one to train)."""
    sz = [p for p, has in records if has]
    if len(sz) < 2:
        raise ValueError(f"need at least 2 seizure records for leave-one-out, got {len(sz)}")
    return [[p] for p in sz]


def cross_patient_folds(ds, root, channels):
    """The plan's cross-patient arm: one fold per patient group (leave one group out), so all of
    a group's records are tested together. Groups keep recordings of the same person together
    (CHB-MIT: chb01 and chb21). Returns (folds, group names); groups without a usable seizure
    record are dropped."""
    folds, names = [], []
    for group in ds.patient_groups(root):
        recs = [p for patient in group for p, _ in ds.usable_records(root, patient, channels)]
        if any(ds.seizures(p) for p in recs):
            folds.append(recs)
            names.append("+".join(group))
    return folds, names
