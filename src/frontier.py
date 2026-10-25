"""Patient-level frontiers and the plan's primary endpoint.

Frontier: for one model, one seed and one patient, false alarms per 24 h against median
latency at each smoothing width, pooled over the patient's folds (so false alarms are
counted over all of the patient's held-out hours).

Median latency treats a missed seizure as censored at +infinity, so it is the plain
median with misses counted as infinitely late (+inf when half or more are missed).

Excess latency (H1, the primary endpoint): FP32's operating point is its default smoothing
(12 s), giving false alarms FA0 at median latency L0. Another model's frontier is the
piecewise-linear curve through its (false alarms, latency) points across all smoothing
widths. Its latency at exactly FA0 is read off that curve by linear interpolation; where
the curve crosses FA0 more than once, the earliest (lowest) latency counts. Excess latency
= that latency - L0. This measures a shift of the curve, not a move along it, and does not
jump with the smoothing grid. If the model's false alarms never come down to FA0, the
excess is +inf (censored); if they are below FA0 even at the least smoothing, the latency
at the least smoothing is used (an upper bound). The same procedure between two FP32 seeds
gives the seed-noise null. Equivalently (H1's second form), delta_fa is the model's false
alarms at exactly L0, interpolated the same way, minus FA0.
"""
import math
from collections import defaultdict

import numpy as np

DEFAULT_SMOOTH = 12


def censored_median(latencies):
    vals = sorted(math.inf if v is None else v for v in latencies)
    if not vals:
        return math.nan
    n = len(vals)
    return vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2


def patient_frontier(rows):
    """rows: frontier rows from all folds of one patient and one seed.
    Returns {(variant, thr_mode): [point sorted by smooth_s]}."""
    acc = defaultdict(lambda: {"tp": 0, "fp": 0, "seizures": 0, "hours": 0.0, "latencies_s": []})
    for r in rows:
        a = acc[(r["variant"], r["thr_mode"], r["smooth_s"])]
        for key in ("tp", "fp", "seizures", "hours"):
            a[key] += r[key]
        a["latencies_s"] += r["latencies_s"]
    out = defaultdict(list)
    for (variant, mode, w), a in acc.items():
        out[(variant, mode)].append({
            "smooth_s": w, "fa_per_24h": a["fp"] / a["hours"] * 24 if a["hours"] else math.nan,
            "fp": a["fp"], "hours": a["hours"], "detected": a["tp"], "seizures": a["seizures"],
            "median_latency_s": censored_median(a["latencies_s"]),
        })
    for v in out.values():
        v.sort(key=lambda p: p["smooth_s"])
    return dict(out)


def operating_point(frontier, w=DEFAULT_SMOOTH):
    return next(p for p in frontier if p["smooth_s"] == w)


def _curve(frontier):
    """(false alarms per 24 h, latency, smoothing) along the frontier, finite latencies only."""
    return [(p["fa_per_24h"], p["median_latency_s"], p["smooth_s"]) for p in frontier
            if math.isfinite(p["median_latency_s"])]


def latency_at_fa(frontier, fa0):
    """Latency the model needs to bring false alarms down to exactly fa0, interpolated along
    its frontier. Returns (latency_s, smoothing_s), smoothing interpolated the same way."""
    pts = _curve(frontier)
    if not pts:
        return math.inf, None
    best = (math.inf, None)
    for (fa_a, la, wa), (fa_b, lb, wb) in zip(pts, pts[1:]):
        if min(fa_a, fa_b) <= fa0 <= max(fa_a, fa_b):
            f = 0.0 if fa_a == fa_b else (fa0 - fa_a) / (fa_b - fa_a)
            lat = la + f * (lb - la)
            if lat < best[0]:
                best = (lat, wa + f * (wb - wa))
    if best[0] == math.inf and pts[0][0] <= fa0:   # already below fa0 at the least smoothing
        best = (pts[0][1], pts[0][2])
    return best


def fa_at_latency(frontier, l0):
    """False alarms per 24 h at exactly latency l0, interpolated along the frontier (the
    lowest, where the curve passes l0 more than once); nan when l0 is outside its range."""
    pts = _curve(frontier)
    best = math.nan
    for (fa_a, la, _), (fa_b, lb, _) in zip(pts, pts[1:]):
        if min(la, lb) <= l0 <= max(la, lb):
            fa = fa_a if la == lb else fa_a + (l0 - la) / (lb - la) * (fa_b - fa_a)
            best = fa if math.isnan(best) else min(best, fa)
    return best


def excess_latency(ref, other, w0=DEFAULT_SMOOTH):
    """Extra latency `other` needs at exactly `ref`'s false alarms (ref at its default smoothing).
    Returns (excess_s, matched_smooth_s, delta_fa_per_24h_at_ref_latency)."""
    p0 = operating_point(ref, w0)
    if not math.isfinite(p0["median_latency_s"]):
        return math.nan, None, math.nan  # undefined: ref itself misses half its seizures
    lat, w = latency_at_fa(other, p0["fa_per_24h"])
    return lat - p0["median_latency_s"], w, fa_at_latency(other, p0["median_latency_s"]) - p0["fa_per_24h"]


def _median(values):
    """Median that keeps +inf (censored) values; nan (undefined) values are dropped."""
    v = sorted(x for x in values if not math.isnan(x))
    if not v:
        return math.nan
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def pooled_excess(by_patient):
    """The pre-registered pooled value: median over seeds within each patient, then median over
    patients. by_patient: {patient: {seed: excess_s}}. Returns (pooled, {patient: value})."""
    per_patient = {p: _median(list(seeds.values())) for p, seeds in by_patient.items()}
    return _median(list(per_patient.values())), per_patient


def seed_band(frontiers_by_seed, w0=DEFAULT_SMOOTH):
    """Excess latency between every ordered pair of FP32 seeds (the null)."""
    seeds = sorted(frontiers_by_seed)
    out = []
    for a in seeds:
        for b in seeds:
            if a != b:
                ex, _, _ = excess_latency(frontiers_by_seed[a], frontiers_by_seed[b], w0)
                out.append(ex)
    return out


def band_95(values):
    """Central 95% interval of finite values (None if fewer than two)."""
    v = np.array([x for x in values if np.isfinite(x)], float)
    return (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) if len(v) >= 2 else None
