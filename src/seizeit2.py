"""SeizeIT2 (OpenNeuro ds005873, BIDS): behind-the-ear wearable EEG.

  - Two EEG channels per recording at 256 Hz. The pair varies: BTEleft+CROSStop,
    BTEright+CROSStop or BTEleft+BTEright. A patient-specific model needs one montage, so
    each subject uses its most common pair (most recording hours); recordings with another
    pair are left out. Channels keep the file's order within a pair.
  - Seizures are the events whose eventType starts with "sz" in each *_events.tsv (onset and
    duration in seconds from the recording start). Impedance checks ("impd") and background
    count as non-seizure.
  - Same causal 0.5-40 Hz band-pass as the other datasets. Each subject is its own group.
"""
import csv
import glob
import os
from collections import Counter
from functools import lru_cache

import numpy as np
import pyedflib

from records import FS, bandpass_causal, cached

NAME = "seizeit2"
CHANNEL_SETS = {"bte2": None}  # the pair is chosen per subject (see montage)
TAGS = {"bte2": "bte2_bp0.5-40_causal4_f16_v1"}


def list_patients(root):
    return sorted(d for d in os.listdir(root) if d.startswith("sub-") and os.path.isdir(os.path.join(root, d)))


def patient_groups(root):
    return [(p,) for p in list_patients(root)]


def list_records(root, patient):
    return sorted(glob.glob(os.path.join(root, patient, "ses-*", "eeg", "*_eeg.edf")))


@lru_cache(maxsize=None)
def _header(edf_path):
    with pyedflib.EdfReader(edf_path) as f:
        return tuple(f.getSignalLabels()), f.getFileDuration()


@lru_cache(maxsize=None)
def montage(root, patient):
    """The subject's channel pair with the most recording hours."""
    hours = Counter()
    for p in list_records(root, patient):
        labels, dur = _header(p)
        hours[labels] += dur
    return hours.most_common(1)[0][0]


@lru_cache(maxsize=None)
def _events(edf_path):
    tsv = edf_path[:-len("_eeg.edf")] + "_events.tsv"
    with open(tsv, newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    return [(float(r["onset"]), float(r["onset"]) + float(r["duration"]))
            for r in rows if r["eventType"].startswith("sz")]


def seizures(edf_path):
    return list(_events(edf_path))


def usable_records(root, patient, channels="bte2"):
    pair = montage(root, patient)
    return [(p, bool(seizures(p))) for p in list_records(root, patient) if _header(p)[0] == pair]


def load_record(edf_path, cache_root=None, channels="bte2"):
    """Returns (x, seizure events, duration): x is (2, n) float16 microvolts at FS."""
    events = seizures(edf_path)

    def compute():
        with pyedflib.EdfReader(edf_path) as f:
            assert all(f.getSampleFrequency(i) == FS for i in range(f.signals_in_file)), f"{edf_path}: not {FS} Hz"
            raw = np.stack([f.readSignal(i) for i in range(f.signals_in_file)])
        return bandpass_causal(raw, FS)

    patient = os.path.basename(edf_path).split("_")[0]
    name = os.path.splitext(os.path.basename(edf_path))[0]
    x = cached(cache_root, NAME, patient, TAGS[channels], name, compute)
    return x, events, x.shape[1] / FS
