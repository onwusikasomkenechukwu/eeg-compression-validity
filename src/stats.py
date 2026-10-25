"""Statistics from the research plan, on per-patient values.

  - Patient bootstrap: resample patients with replacement; interval for a pooled statistic.
  - Concentration: share of the total (positive) shift carried by the worst 20% of patients.
  - Mixed-effects model: excess latency ~ 1 + (1 | patient) on patient-seed values (the
    design Reisinger et al. 2025 used), finite values only.
  - H3 predictor (dwell): fraction of a patient's FP32 test windows whose score lies within
    DELTA logits of the FP32 threshold. It uses only the FP32 model, before any quantization,
    so H3 is a prediction, not a fit. DELTA is fixed in advance; other widths are reported as
    sensitivity analyses.
  - H3 premise: autocorrelation over time of the quantization error (quantized minus FP32
    logit) within each test record. Weak correlation means errors near the threshold flip
    decisions independently from second to second, which smoothing must then absorb.
"""
import math

import numpy as np

DELTA = 0.5          # logits; pre-registered dwell band half-width
DELTA_SENSITIVITY = (0.25, 0.5, 1.0)


def logit(p, eps=1e-6):
    p = np.clip(np.asarray(p, float), eps, 1 - eps)
    return np.log(p / (1 - p))


def dwell(scores, threshold, delta=DELTA):
    """Fraction of windows whose score is within delta logits of the threshold."""
    return float(np.mean(np.abs(logit(scores) - logit(threshold)) <= delta))


def error_autocorr(fp32, quant, lengths, lags=(1, 2, 4, 8)):
    """Autocorrelation of (quant - fp32) logit differences at the given lags (in 1 s steps),
    pooled over records without crossing record boundaries."""
    d = logit(quant) - logit(fp32)
    out = {}
    for lag in lags:
        a, b = [], []
        i = 0
        for n in lengths:
            seg = d[i:i + n]
            i += n
            if n > lag:
                a.append(seg[:-lag])
                b.append(seg[lag:])
        a, b = np.concatenate(a), np.concatenate(b)
        out[lag] = float(np.corrcoef(a, b)[0, 1]) if a.std() > 0 and b.std() > 0 else math.nan
    return out


def _median_keep_inf(v):
    v = sorted(x for x in v if not math.isnan(x))
    if not v:
        return math.nan
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def bootstrap_ci(per_patient, stat=_median_keep_inf, n_boot=2000, seed=0, level=0.95):
    """Percentile interval of stat over patients resampled with replacement."""
    vals = [v for v in per_patient if not math.isnan(v)]
    if len(vals) < 2:
        return (math.nan, math.nan)
    rng = np.random.default_rng(seed)
    boots = [stat(list(rng.choice(vals, size=len(vals), replace=True))) for _ in range(n_boot)]
    lo, hi = np.percentile(boots, [100 * (1 - level) / 2, 100 * (1 + level) / 2])
    return float(lo), float(hi)


def concentration(per_patient, top=0.2):
    """Share of the summed positive shift carried by the worst `top` fraction of patients
    (censored +inf values count as the largest; nan if there is no positive shift)."""
    v = sorted((x for x in per_patient if not math.isnan(x)), reverse=True)
    if not v:
        return math.nan
    if math.isinf(v[0]):
        return 1.0
    pos = [max(x, 0.0) for x in v]
    total = sum(pos)
    if total == 0:
        return math.nan
    k = max(1, math.ceil(top * len(v)))
    return sum(pos[:k]) / total


def mixed_model(values):
    """values: [(patient, seed, excess)]. Fits excess ~ 1 + (1 | patient) on finite values.
    Returns {"mean", "ci", "patient_sd", "residual_sd", "n", "n_patients"} or None."""
    import pandas as pd
    import statsmodels.formula.api as smf
    rows = [(p, s, x) for p, s, x in values if math.isfinite(x)]
    df = pd.DataFrame(rows, columns=["patient", "seed", "excess"])
    if df["patient"].nunique() < 3:
        return None
    res = smf.mixedlm("excess ~ 1", df, groups=df["patient"]).fit(reml=True)
    lo, hi = res.conf_int().loc["Intercept"]
    return {"mean": float(res.params["Intercept"]), "ci": (float(lo), float(hi)),
            "patient_sd": float(math.sqrt(max(res.cov_re.iloc[0, 0], 0.0))),
            "residual_sd": float(math.sqrt(res.scale)), "n": len(df), "n_patients": int(df["patient"].nunique())}


def spearman(x, y):
    """Spearman rank correlation of paired finite values (nan with fewer than 3 pairs)."""
    from scipy.stats import spearmanr
    pairs = [(a, b) for a, b in zip(x, y) if math.isfinite(a) and math.isfinite(b)]
    if len(pairs) < 3:
        return math.nan
    return float(spearmanr(*zip(*pairs)).statistic)
