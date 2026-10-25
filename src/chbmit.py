"""CHB-MIT (PhysioNet chbmit 1.0.0): loading, labels and patient groups.

Choices not fixed by the plan or EpiDeNet, to be stated in the pre-registration:
  - EpiDeNet's four temporal channels are taken as F7-T7, T7-P7, F8-T8, T8-P8 (the
    paper says only "4 channels in the temporal region"). T8-P8 appears twice in the
    CHB-MIT montage; the first copy is used (also for the 18-channel set).
  - Causal 0.5-40 Hz 4th-order Butterworth band-pass (records.bandpass_causal). EpiDeNet
    does not describe its filtering. CHB-MIT records are near zero-mean, so the causal
    filter has no start-up artifact.
  - Signals are cached as float16 microvolts (physical range +/-2000 uV, well inside
    float16), under a folder named by the channel set's tag so a change in preprocessing
    can never reuse an old cache.
  - Records without the chosen channels (three chb12 records for the temporal set) are left
    out before folds are built, so every fold tests on a seizure.
  - Seizure times come from the summary files (as in SzCORE's converter). They agree with the
    .seizures annotation files on every record except chb24_21, where the summary gives an
    onset of 2804 s and the annotation file 2404 s (same offset, 2872 s).
  - chb21 is the same subject as chb01 (PhysioNet; recorded 1.5 years later), so the
    cross-patient arm keeps them in one group.
"""
import glob
import os

import numpy as np
import pyedflib
from epilepsy2bids.load_annotations.chbmit import loadAnnotationsFromEdf

from records import FS, bandpass_causal, cached, make_folds, seizure_fraction, window_starts  # noqa: F401

NAME = "chbmit"
TEMPORAL = ["F7-T7", "T7-P7", "F8-T8", "T8-P8"]
BIPOLAR18 = [  # Ahlawat (2026), from his public code
    "FP1-F7", "F7-T7", "T7-P7", "P7-O1", "FP1-F3", "F3-C3", "C3-P3", "P3-O1",
    "FP2-F4", "F4-C4", "C4-P4", "P4-O2", "FP2-F8", "F8-T8", "T8-P8", "P8-O2", "FZ-CZ", "CZ-PZ",
]
CHANNEL_SETS = {"temporal4": TEMPORAL, "bipolar18": BIPOLAR18}
TAGS = {"temporal4": "temporal4_bp0.5-40_causal4_f16_v1", "bipolar18": "bipolar18_bp0.5-40_causal4_f16_v1"}
PREP_TAG = TAGS["temporal4"]
SAME_SUBJECT = [("chb01", "chb21")]


def list_patients(root):
    return sorted(d for d in os.listdir(root) if d.startswith("chb") and os.path.isdir(os.path.join(root, d)))


def patient_groups(root):
    """Patients grouped by person, for leave-one-group-out splits."""
    groups, seen = [], set()
    for p in list_patients(root):
        if p in seen:
            continue
        g = next((tuple(x for x in pair if x in list_patients(root)) for pair in SAME_SUBJECT if p in pair), (p,))
        groups.append(g)
        seen.update(g)
    return groups


def list_records(data_root, patient):
    # chb17's records are named chb17a_*, chb17b_*, chb17c_*, so match any suffix.
    return sorted(glob.glob(os.path.join(data_root, patient, f"{patient}*.edf")))


def has_channels(edf_path, channels="temporal4"):
    with pyedflib.EdfReader(edf_path) as f:
        labels = f.getSignalLabels()
    return all(ch in labels for ch in CHANNEL_SETS[channels])


def usable_records(data_root, patient, channels="temporal4"):
    """[(path, has_seizure)] for the records that have every channel in the set."""
    return [(p, bool(seizures(p))) for p in list_records(data_root, patient) if has_channels(p, channels)]


def seizures(edf_path):
    """[(onset, offset)] in seconds, from the patient's summary file."""
    return loadAnnotationsFromEdf(edf_path).getEvents()


def load_record(edf_path, cache_root=None, channels="temporal4"):
    """Returns (x, seizure events, duration): x is (C, n) float16 microvolts at FS, or None
    when the record lacks one of the channels."""
    events = seizures(edf_path)
    names = CHANNEL_SETS[channels]

    def compute():
        with pyedflib.EdfReader(edf_path) as f:
            labels = f.getSignalLabels()
            if any(ch not in labels for ch in names):
                return None
            idx = [labels.index(ch) for ch in names]  # index() picks the first T8-P8
            assert all(f.getSampleFrequency(i) == FS for i in idx), f"{edf_path}: not {FS} Hz"
            raw = np.stack([f.readSignal(i) for i in idx])  # physical units: microvolts
        return bandpass_causal(raw, FS)

    patient = os.path.basename(os.path.dirname(edf_path))
    name = os.path.splitext(os.path.basename(edf_path))[0]
    x = cached(cache_root, NAME, patient, TAGS[channels], name, compute)
    if x is None:
        with pyedflib.EdfReader(edf_path) as f:
            return None, events, f.getFileDuration()
    return x, events, x.shape[1] / FS
