"""SzCORE event scoring plus the research plan's latency metric."""
from timescoring.annotations import Annotation
from timescoring.scoring import EventScoring

# SzCORE (Dan et al. 2024): 30 s pre-ictal and 60 s post-ictal tolerance, events closer
# than 90 s merged, events longer than 300 s split, any overlap counts.
SZCORE = EventScoring.Parameters(
    toleranceStart=30,
    toleranceEnd=60,
    minOverlap=0,
    maxEventDuration=5 * 60,
    minDurationBetweenEvents=90,
)


def detection_latencies(ref_events, hyp_events, param: EventScoring.Parameters = SZCORE):
    """Latency per annotated seizure, as defined in the research plan.

    Seconds from the annotated onset to the first alarm overlapping the seizure's tolerance
    window [onset - toleranceStart, offset + toleranceEnd]. Negative when the alarm falls
    inside the pre-ictal tolerance; an alarm already on when the window opens counts from
    the window start. None marks a missed seizure (censored).

    Measured on the raw alarms and the annotated seizures, not on SzCORE's merged/split
    events: merging would let a false alarm up to 90 s before a seizure pass as an early
    detection, and splitting a seizure longer than 300 s would add latencies measured from
    artificial onsets.
    """
    latencies = []
    for onset, offset in sorted(ref_events):
        lo, hi = onset - param.toleranceStart, offset + param.toleranceEnd
        starts = [max(h0, lo) for h0, h1 in hyp_events if h0 < hi and h1 > lo]
        latencies.append(min(starts) - onset if starts else None)
    return latencies


def score_record(ref_events, hyp_events, duration, fs=256, param=SZCORE):
    """Event-score one record; events are (start, end) in seconds. Returns (score, latencies):
    SzCORE counts in score (tp, fp, refTrue), one latency per annotated seizure."""
    n = round(duration * fs)
    # timescoring's merge step assumes events in time order; unsorted input silently
    # drops detections, so always sort.
    ref = Annotation(sorted(ref_events), fs, n)
    hyp = Annotation(sorted(hyp_events), fs, n)
    return EventScoring(ref, hyp, param), detection_latencies(ref_events, hyp_events, param)
