"""Correctness tests for the pipeline's building blocks. Run: python -m pytest tests -q"""
import math
import os
import sys

import numpy as np
import pytest
import torch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from chbmit import FS, make_folds, seizure_fraction, window_starts  # noqa: E402
from epidenet import EpiDeNet  # noqa: E402
from frontier import censored_median, excess_latency, pooled_excess, seed_band  # noqa: E402
from pipeline import EPIDENET, alarm_raw, load_fp32, smooth_seconds, smooth_votes, to_events  # noqa: E402
from quantize import QAT, FakeQuant, OnnxInt8, fold_bn  # noqa: E402
from stats import bootstrap_ci, concentration, dwell, error_autocorr, mixed_model  # noqa: E402

WIN = EPIDENET.win
from scoring import score_record  # noqa: E402


# --- scoring (SzCORE rules and the plan's latency) -------------------------------------------

REF = [(2996.0, 3036.0)]


@pytest.mark.parametrize("hyp, tp, fp, lat", [
    ([(3004.0, 3041.0)], 1, 0, 8.0),                      # detected 8 s late
    ([(2986.0, 3036.0)], 1, 0, -10.0),                    # inside the 30 s pre-ictal tolerance
    ([(600.0, 610.0)], 0, 1, None),                       # missed + one false alarm
    ([(3004.0, 3036.0), (300.0, 304.0), (364.0, 368.0)], 1, 1, 8.0),   # 60 s gap: merged
    ([(3004.0, 3036.0), (300.0, 304.0), (424.0, 428.0)], 1, 2, 8.0),   # 120 s gap: separate
    ([(300.0, 304.0), (3004.0, 3036.0)][::-1], 1, 1, 8.0),            # unsorted input is sorted
])
def test_szcore_scoring(hyp, tp, fp, lat):
    s, lats = score_record(REF, hyp, 3600.0)
    assert (s.tp, s.fp, lats[0]) == (tp, fp, lat)


def test_false_alarm_before_seizure_is_not_an_early_detection():
    # SzCORE merges an alarm 70 s before onset with the real detection (gap < 90 s), so the
    # merged event starts at -70 s; latency must still come from the real alarm at +8 s.
    s, lats = score_record(REF, [(2926.0, 2930.0), (3004.0, 3036.0)], 3600.0)
    assert s.tp == 1 and lats == [8.0]


def test_long_seizure_gets_one_latency_from_its_true_onset():
    # SzCORE splits a 600 s seizure into 300 s pieces; latency is per annotated seizure.
    s, lats = score_record([(1000.0, 1600.0)], [(1010.0, 1600.0)], 3600.0)
    assert s.refTrue == 2 and s.tp == 2
    assert lats == [10.0]


# --- smoothing and alarm timing ----------------------------------------------------------------

def test_vote_and_seconds_smoothing():
    p = np.array([0, 1, 0, 0, 1, 1, 0, 1, 0, 0], bool)
    assert smooth_votes(p).astype(int).tolist() == [0, 0, 0, 0, 0, 1, 1, 1, 0, 0]
    # W = 3 s at a 1 s hop: alarm when more than half of the last 3 decisions are positive.
    assert smooth_seconds(p, 3).astype(int).tolist() == [0, 0, 0, 0, 0, 1, 1, 1, 0, 0]
    assert smooth_seconds(np.ones(5, bool), 12).all()      # partial history at the start


def test_threshold_keeps_specificity_with_tied_scores():
    # A collapsed quantized model: 90% of seizure-free windows share its top score, so the
    # 99.5% quantile lands on the tie (as for 4-bit Ahlawat on chb01).
    rng = np.random.default_rng(0)
    neg = np.concatenate([np.full(9000, 0.9), rng.uniform(0, 0.5, 1000)])
    thr = float(np.quantile(neg, 0.995))
    assert np.mean(~alarm_raw(neg, thr)) >= 0.995           # target met despite the ties
    assert np.mean(neg < thr) < 0.5                         # what '>=' would have given


def test_alarm_is_timed_at_window_end():
    alarm = np.zeros(100, bool)
    alarm[10:13] = True                                     # windows starting at 10, 11, 12 s
    ev = to_events(alarm, duration=104.0)
    assert ev == [(14.0, 17.0)]                             # first decision at 10 + 4 s
    s, lats = score_record([(12.0, 40.0)], ev, 104.0)
    assert lats == [2.0]


# --- windows, labels, folds ----------------------------------------------------------------------

def test_seizure_fraction_and_folds():
    starts = window_starts(20 * FS, WIN, WIN)
    assert seizure_fraction(starts, WIN, [(6.0, 10.0)], 20 * FS).tolist() == [0, 0.5, 0.5, 0, 0]
    recs = [(f"r{i}", i in (2, 5, 9)) for i in range(12)]
    folds = make_folds(recs)
    assert len(folds) == 3
    flat = [p for f in folds for p in f]
    assert sorted(flat) == sorted(p for p, _ in recs)       # every record exactly once
    assert all(sum(dict(recs)[p] for p in f) == 1 for f in folds)  # one seizure record per fold


# --- quantization --------------------------------------------------------------------------------

def _synthetic(n, gen):
    """Noise windows; class 1 adds an 8 Hz rhythm of random amplitude (a seizure stand-in)."""
    y = torch.randint(0, 2, (n,), generator=gen)
    t = torch.arange(1024) / FS
    amp = (0.3 + torch.rand(n, 1, 1, 1, generator=gen)) * y[:, None, None, None]
    x = torch.randn(n, 1, 4, 1024, generator=gen) + amp * torch.sin(2 * math.pi * 8 * t)
    return x, y


@pytest.fixture(scope="module")
def trained_like_model():
    """A briefly trained model: an untrained one outputs a near-constant score, so any
    quantization noise swamps it and agreement tests mean nothing."""
    torch.manual_seed(0)
    gen = torch.Generator().manual_seed(0)
    m = EpiDeNet()
    opt = torch.optim.Adam(m.parameters(), lr=3e-3)
    for _ in range(60):
        x, y = _synthetic(64, gen)
        opt.zero_grad()
        torch.nn.functional.cross_entropy(m(x), y).backward()
        opt.step()
    x, _ = _synthetic(256, gen)
    return m.eval(), x


def test_fold_bn_is_exact(trained_like_model):
    m, x = trained_like_model
    with torch.no_grad():
        assert torch.allclose(m(x), fold_bn(m)(x), atol=1e-4)


def test_fake_quant_error_grows_as_bits_fall(trained_like_model):
    m, x = trained_like_model
    with torch.no_grad():
        ref = m(x)
        err = {b: (FakeQuant(m, b).calibrate(x)(x) - ref).abs().mean().item() for b in (16, 8, 6, 4)}
    assert err[16] < 1e-3
    assert err[16] < err[8] < err[6] < err[4]


def test_onnx_int8_matches_export_and_simulation(trained_like_model):
    m, x = trained_like_model
    q = OnnxInt8(m, x, n_calib=256)
    with torch.no_grad():
        ref = m(x)
        assert (ref - q(x, fp32=True)).abs().max().item() < 1e-3   # FP32 export is faithful
        int8, sim8 = q(x), FakeQuant(m, 8).calibrate(x)(x)
    # Real INT8 kernels and the 8-bit simulation both track FP32's decision score closely.
    d = lambda a: (a[:, 1] - a[:, 0]).numpy()  # noqa: E731
    assert d(ref).std() > 1.0                                # the model really discriminates
    assert np.corrcoef(d(int8), d(ref))[0, 1] > 0.99
    assert np.corrcoef(d(sim8), d(ref))[0, 1] > 0.99
    assert np.corrcoef(d(int8), d(sim8))[0, 1] > 0.98


def test_qat_starts_as_sim8_trains_and_stays_on_the_grid(trained_like_model):
    m, x = trained_like_model
    qat = QAT(m, 8).calibrate(x).eval()
    with torch.no_grad():
        # Before any fine-tuning, QAT inference is exactly the simulated 8-bit model.
        assert torch.allclose(qat(x), FakeQuant(m, 8).calibrate(x)(x), atol=1e-5)

    # Gradients reach the underlying weights through the straight-through estimator.
    gen = torch.Generator().manual_seed(1)
    qat.train()
    opt = torch.optim.Adam(qat.parameters(), lr=1e-3)
    conv = qat.net.features[1][0]
    before = conv.parametrizations.weight.original.detach().clone()
    losses = []
    for _ in range(20):
        xb, yb = _synthetic(64, gen)
        opt.zero_grad()
        loss = torch.nn.functional.cross_entropy(qat(xb), yb)
        loss.backward()
        opt.step()
        losses.append(loss.item())
    assert not torch.equal(before, conv.parametrizations.weight.original)
    assert np.mean(losses[-5:]) < 0.5

    # The weights the model computes with sit on a per-channel 8-bit grid.
    qat.eval()
    w = conv.weight.detach().reshape(conv.weight.shape[0], -1)
    for row in w:
        assert len(torch.unique(row)) <= 255
        step = row.abs().max() / 127
        assert torch.allclose(row / step, torch.round(row / step), atol=1e-3)


def test_saved_fp32_weights_rebuild_the_model(trained_like_model, tmp_path):
    m, x = trained_like_model
    mean, std = np.zeros((4, 1), np.float32), np.ones((4, 1), np.float32)
    np.savez(tmp_path / "job.npz", norm_mean=mean, norm_std=std,
             **{f"w_fp32__{n}": v.numpy() for n, v in m.state_dict().items()})
    m2, mean2, std2 = load_fp32(np.load(tmp_path / "job.npz"))
    with torch.no_grad():
        assert torch.equal(m(x), m2(x))
    assert np.array_equal(mean, mean2) and np.array_equal(std, std2)


# --- frontier and the primary endpoint ---------------------------------------------------------

def _front(points):
    return [{"smooth_s": w, "fp": fp, "hours": 10.0, "fa_per_24h": fp / 10 * 24, "median_latency_s": lat,
             "detected": 1, "seizures": 1} for w, fp, lat in points]


def test_censored_median():
    assert censored_median([3.0, 5.0, None]) == 5.0
    assert censored_median([3.0, None, None]) == math.inf
    assert censored_median([2.0, 4.0]) == 3.0


def test_excess_latency_interpolates_along_frontier():
    fp32 = _front([(12, 4, 10.0), (16, 2, 13.0), (20, 1, 16.0)])       # FA0 = 9.6/24h at 10 s
    worse = _front([(12, 6, 10.0), (16, 4, 14.0), (20, 2, 18.0)])
    ex, w, dfa = excess_latency(fp32, worse)
    assert (ex, w) == (4.0, 16)                              # reaches 9.6/24h exactly at 14 s
    assert dfa == pytest.approx(4.8)                         # at 10 s it raises 14.4 vs 9.6 per 24 h
    between = _front([(12, 8, 10.0), (16, 2, 14.0)])         # 19.2 -> 4.8 per 24 h
    ex, w, _ = excess_latency(fp32, between)
    assert ex == pytest.approx(8 / 3) and w == pytest.approx(16 - 4 / 3)  # 2/3 of the way along
    never = _front([(12, 9, 10.0), (16, 8, 14.0), (20, 7, 18.0)])
    assert excess_latency(fp32, never)[0] == math.inf       # censored
    below = _front([(4, 1, 6.0), (12, 0, 9.0)])              # under FA0 even at least smoothing
    assert excess_latency(fp32, below)[0] == -4.0            # upper bound: its 4 s point
    assert excess_latency(fp32, fp32)[0] == 0.0
    assert sorted(seed_band({0: fp32, 1: worse})) == [0.0, 4.0]
    blind = _front([(12, 4, math.inf), (16, 2, math.inf)])   # reference misses half its seizures
    assert math.isnan(excess_latency(blind, worse)[0])       # undefined, not censored


def test_pooled_excess_is_median_of_patient_medians():
    pooled, per = pooled_excess({"a": {0: 1.0, 1: 2.0, 2: 9.0}, "b": {0: 0.0, 1: 0.5, 2: math.nan},
                                 "c": {0: math.inf, 1: math.inf, 2: 3.0}})
    assert per == {"a": 2.0, "b": 0.25, "c": math.inf}
    assert pooled == 2.0


def test_make_folds_needs_three_seizure_records():
    with pytest.raises(ValueError):
        make_folds([("a", True), ("b", True), ("c", False)])


# --- statistics (Stage 1) -------------------------------------------------------------------------

def test_dwell_concentration_bootstrap():
    assert dwell(np.array([0.5, 0.5, 0.99, 0.01]), 0.5, delta=0.5) == 0.5
    assert concentration([10.0, 0.0, 0.0, 0.0, 0.0]) == 1.0          # worst 20% (1 of 5) carries it all
    assert concentration([1.0] * 10) == pytest.approx(0.2)            # evenly spread
    assert concentration([math.inf, 1.0, 0.0]) == 1.0                 # a censored patient dominates
    ci1, ci2 = bootstrap_ci([1.0, 2.0, 3.0, 4.0]), bootstrap_ci([1.0, 2.0, 3.0, 4.0])
    assert ci1 == ci2 and ci1[0] <= 2.5 <= ci1[1]                     # deterministic, covers the median


def test_error_autocorr_white_vs_persistent():
    rng = np.random.default_rng(0)
    p = rng.uniform(0.05, 0.95, 20000)
    white = 1 / (1 + np.exp(-(np.log(p / (1 - p)) + rng.normal(0, 0.1, p.size))))
    assert abs(error_autocorr(p, white, [p.size])[1]) < 0.05
    slow = np.repeat(rng.normal(0, 0.1, p.size // 10), 10)            # error constant for 10 steps
    persistent = 1 / (1 + np.exp(-(np.log(p / (1 - p)) + slow)))
    assert error_autocorr(p, persistent, [p.size])[1] > 0.8


def test_mixed_model_recovers_mean():
    rng = np.random.default_rng(1)
    vals = [(f"p{i}", s, 2.0 + off + rng.normal(0, 0.3)) for i, off in enumerate(rng.normal(0, 1, 12)) for s in range(3)]
    mm = mixed_model(vals)
    assert mm["ci"][0] < 2.0 < mm["ci"][1] and mm["n_patients"] == 12


# --- datasets (skipped when the data is not on this machine) -------------------------------------

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


@pytest.mark.skipif(not os.path.isdir(os.path.join(DATA, "siena")), reason="Siena not downloaded")
def test_siena_annotations_parse_to_physionet_total():
    import siena
    counts = siena.audit_annotations(os.path.join(DATA, "siena"))
    assert all(isinstance(v, int) for v in counts.values()), counts
    assert sum(counts.values()) == siena.EXPECTED_SEIZURES


@pytest.mark.skipif(not os.path.isdir(os.path.join(DATA, "chbmit")), reason="CHB-MIT not downloaded")
def test_chbmit_counts_and_groups():
    import chbmit
    root = os.path.join(DATA, "chbmit")
    groups = chbmit.patient_groups(root)
    assert ("chb01", "chb21") in groups and len(groups) == 23
    recs = [r for p in chbmit.list_patients(root) for r in chbmit.usable_records(root, p)]
    assert len(recs) == 683 and sum(h for _, h in recs) == 138
    assert sum(len(chbmit.seizures(r)) for r, _ in recs) == 185
