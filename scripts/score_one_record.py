"""Week-1 check: SzCORE event scoring plus the plan's latency metric on one CHB-MIT record.

Loads the reference annotation for one record with epilepsy2bids, builds synthetic
hypotheses whose correct scores are known in advance, scores them with src/scoring.py
under SzCORE's parameters, and asserts the results.

Usage: python scripts/score_one_record.py [path/to/record.edf]
"""
import os
import sys

from epilepsy2bids.load_annotations.chbmit import loadAnnotationsFromEdf

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
from scoring import score_record  # noqa: E402


def main():
    edf = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "chbmit", "chb01", "chb01_03.edf")
    ann = loadAnnotationsFromEdf(edf)
    duration = ann.events[0]["recordingDuration"]
    ref_events = ann.getEvents()
    assert ref_events, f"{edf} has no seizures; pick a seizure record"
    onset, offset = ref_events[0]
    print(f"{os.path.basename(edf)}: {duration:.0f} s, seizures {ref_events}")

    # Each case: (description, hypothesis events, expected tp, expected fp, expected first latency)
    cases = [
        ("detected 8 s after onset", [(onset + 8, offset + 5)], 1, 0, 8.0),
        ("detected 10 s before onset (inside 30 s pre-ictal tolerance)", [(onset - 10, offset)], 1, 0, -10.0),
        ("missed; one false alarm far away", [(600, 610)], 0, 1, None),
        ("detected + two fragments 60 s apart (merged into 1 FA by the 90 s rule)",
         [(onset + 8, offset), (300, 304), (364, 368)], 1, 1, 8.0),
        ("detected + two fragments 120 s apart (2 FAs)",
         [(onset + 8, offset), (300, 304), (424, 428)], 1, 2, 8.0),
    ]
    ok = True
    for desc, hyp_events, tp, fp, lat in cases:
        s, lats = score_record(ref_events, hyp_events, duration)
        got = (s.tp, s.fp, lats[0])
        passed = got == (tp, fp, lat)
        ok &= passed
        fp24 = s.fp / (duration / 86400)
        print(f"  [{'ok' if passed else 'FAIL'}] {desc}: tp={s.tp}/{s.refTrue} fp={s.fp} "
              f"({fp24:.0f}/24h on this 1-h file) latency={lats[0]}"
              + ("" if passed else f"  expected tp={tp} fp={fp} latency={lat}"))
    print("all checks passed" if ok else "SOME CHECKS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
