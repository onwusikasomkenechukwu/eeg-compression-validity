"""Siena Scalp EEG (PhysioNet siena-scalp-eeg 1.0.0): loading, labels, patients.

  - 512 Hz referential EEG, old 10-20 names (T3/T4/T5/T6 = T7/T8/P7/P8). EpiDeNet's four
    temporal bipolar channels are built by subtraction: F7-T3, T3-T5, F8-T4, T4-T6 (the
    same derivations as CHB-MIT's F7-T7, T7-P7, F8-T8, T8-P8), then band-passed causally
    at 512 Hz and decimated to 256 Hz (records.bandpass_causal).
  - Seizure times are parsed from Seizures-list-PNxx.txt, which mixes "." and ":" in clock
    times, spells some file names differently from the files (PNO6 for PN06, "PN11-" for
    PN11-1), and lists recordings that cross midnight. Clock times are converted to seconds
    from each EDF's own header start time, wrapping past midnight; every seizure must fall
    inside its recording, and the total must match PhysioNet's 47.
  - Each patient is their own group (no repeated subjects).
"""
import glob
import os
import re
from functools import lru_cache

import numpy as np
import pyedflib

from records import FS, bandpass_causal, cached

NAME = "siena"
CHANNEL_SETS = {"temporal4": [("EEG F7", "EEG T3"), ("EEG T3", "EEG T5"), ("EEG F8", "EEG T4"), ("EEG T4", "EEG T6")]}
TAGS = {"temporal4": "temporal4_bp0.5-40_causal4_ds2_f16_v1"}
EXPECTED_SEIZURES = 47

# Errors in the published seizure lists, corrected explicitly (state in the pre-registration).
NAME_FIXES = {
    "PN01.EDF": "PN01-1.EDF",   # the patient's only file
    "PN11-.EDF": "PN11-1.EDF",  # the patient's only file
}
TIME_FIXES = {
    # PN00-3.edf runs 18:15:44-18:57:13; the listed seizure end 19.29.29 falls after the
    # recording. Read as 18.29.29: a 60 s seizure, like PN00's others (60-70 s).
    ("PN00-3.EDF", "19.29.29"): "18.29.29",
}


def list_patients(root):
    return sorted(d for d in os.listdir(root) if d.startswith("PN") and os.path.isdir(os.path.join(root, d)))


def patient_groups(root):
    return [(p,) for p in list_patients(root)]


def list_records(root, patient):
    return sorted(glob.glob(os.path.join(root, patient, "*.edf")))


@lru_cache(maxsize=None)
def _header(edf_path):
    """(labels, start time, duration) of an EDF, read once and closed."""
    with pyedflib.EdfReader(edf_path) as f:
        return tuple(f.getSignalLabels()), f.getStartdatetime(), f.getFileDuration()


def _clock(s):
    h, m, sec = (int(x) for x in re.findall(r"\d+", s)[:3])
    return h * 3600 + m * 60 + sec


def _norm(name):
    """Normalize a file name as written in the seizure list (letter O for zero, known errors)."""
    name = name.strip().upper().replace("PNO", "PN0")
    return NAME_FIXES.get(name, name)


@lru_cache(maxsize=None)
def _patient_seizures(root, patient):
    """{edf path: [(onset_s, offset_s)]} for one patient, validated against the EDF headers."""
    edfs = {_norm(os.path.basename(p)): p for p in list_records(root, patient)}
    out = {p: [] for p in edfs.values()}
    text = open(os.path.join(root, patient, f"Seizures-list-{patient}.txt"), encoding="latin-1").read()
    current, start = None, None
    for line in text.splitlines():
        low = line.strip().lower()
        if low.startswith("file name"):
            current = edfs[_norm(line.split(":", 1)[1])]
        elif re.match(r"(seizure )?start time", low):
            start = _clock(line.split(":", 1)[1])
        elif re.match(r"(seizure )?end time", low) and start is not None:
            raw = line.split(":", 1)[1].strip()
            end = _clock(TIME_FIXES.get((_norm(os.path.basename(current)), raw), raw))
            _, t0, dur = _header(current)
            base = t0.hour * 3600 + t0.minute * 60 + t0.second
            on = (start - base) % 86400
            off = (end - base) % 86400
            if not 0 <= on < off <= dur:
                raise ValueError(f"{patient}: seizure {_fmt(start)}-{_fmt(end)} does not fit "
                                 f"{os.path.basename(current)} (starts {t0.time()}, {dur:.0f} s)")
            out[current].append((float(on), float(off)))
            start = None
    return out


def _fmt(s):
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def audit_annotations(root):
    """Every patient's list parsed separately; returns {patient: count or error message}."""
    res = {}
    for p in list_patients(root):
        try:
            res[p] = sum(len(v) for v in _patient_seizures(root, p).values())
        except Exception as e:  # report all problems at once
            res[p] = f"ERROR {e}"
    return res


def seizures(edf_path):
    root, patient = os.path.dirname(os.path.dirname(edf_path)), os.path.basename(os.path.dirname(edf_path))
    return _patient_seizures(root, patient)[edf_path]


def usable_records(root, patient, channels="temporal4"):
    need = {ch for pair in CHANNEL_SETS[channels] for ch in pair}
    return [(p, bool(seizures(p))) for p in list_records(root, patient) if need <= set(_header(p)[0])]


def load_record(edf_path, cache_root=None, channels="temporal4"):
    """Returns (x, seizure events, duration): x is (4, n) float16 microvolts at FS."""
    events = seizures(edf_path)

    def compute():
        with pyedflib.EdfReader(edf_path) as f:
            labels = f.getSignalLabels()
            sig = {}
            for a, b in CHANNEL_SETS[channels]:
                for ch in (a, b):
                    if ch not in sig:
                        i = labels.index(ch)
                        assert f.getSampleFrequency(i) == 512, f"{edf_path}: {ch} not 512 Hz"
                        sig[ch] = f.readSignal(i)
        raw = np.stack([sig[a] - sig[b] for a, b in CHANNEL_SETS[channels]])
        return bandpass_causal(raw, 512)

    patient = os.path.basename(os.path.dirname(edf_path))
    name = os.path.splitext(os.path.basename(edf_path))[0]
    x = cached(cache_root, NAME, patient, TAGS[channels], name, compute)
    return x, events, x.shape[1] / FS


def check_annotations(root):
    """Parse every patient's list; returns (total seizures, {patient: count})."""
    counts = {p: sum(len(v) for v in _patient_seizures(root, p).values()) for p in list_patients(root)}
    return sum(counts.values()), counts
