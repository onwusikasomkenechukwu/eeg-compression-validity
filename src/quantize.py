"""Quantization of a trained EpiDeNet.

Post-training quantization, paired on the same FP32 weights; two paths, both calibrated on
training windows:
  - onnx_int8: ONNX Runtime static INT8 (QDQ format), per-channel symmetric INT8 weights,
    per-tensor activations, MinMax calibration. This is the primary condition: the
    scheme TFLite Micro and CMSIS-NN use, run as real integer kernels on the CPU.
  - FakeQuant(bits): simulated b-bit quantization in PyTorch (Nagel et al. 2021):
    BatchNorm folded into the convolutions, per-output-channel symmetric weights,
    per-tensor asymmetric activations at the input of every conv/linear layer, ranges
    from calibration min/max. Used for the 6- and 4-bit dose-response; the 8-bit
    version cross-checks the ONNX INT8 path. FakeQuant(4, act_bits=8) is W4A8, the
    sub-8-bit scheme some deployment stacks support (4-bit weights, 8-bit activations);
    exploratory, added after registration.
  - Float16Sim: FP16 weights and layer inputs (rounded to half precision), FP32 accumulation;
    exploratory, added after registration.

Quantization-aware training (QAT), the plan's retrained condition, compared only against
the FP32 seed band because retraining mixes quantization with training noise:
  - QAT(bits): fine-tunes the job's own FP32 model (Jacob et al. 2018; Krishnamoorthi 2018)
    with BatchNorm folded first (as deployed), per-output-channel symmetric weights and
    per-tensor asymmetric activations fake-quantized in the forward pass, straight-through
    gradients. Activation ranges start from calibration min/max and follow an exponential
    moving average during training; they are buffers, so the best epoch's ranges are kept
    with its weights. Evaluated as simulated 8-bit inference (the sim8 path tracks real
    ONNX INT8 closely, see tests), frozen ranges.
"""
import copy
import os
import tempfile

import numpy as np
import torch
import torch.nn as nn
from torch.nn.utils import parametrize


CONV = (nn.Conv1d, nn.Conv2d)
QUANT_LAYERS = (nn.Conv1d, nn.Conv2d, nn.Linear)


def fold_bn(model):
    """Copy of model with every convolution -> BatchNorm pair (adjacent inside an nn.Sequential)
    folded into the convolution. Models without BatchNorm are returned unchanged (a copy)."""
    m = copy.deepcopy(model).eval()
    for seq in [s for s in m.modules() if isinstance(s, nn.Sequential)]:
        for i in range(len(seq) - 1):
            conv, bn = seq[i], seq[i + 1]
            if not (isinstance(conv, CONV) and isinstance(bn, (nn.BatchNorm1d, nn.BatchNorm2d))):
                continue
            scale = bn.weight / torch.sqrt(bn.running_var + bn.eps)
            conv.weight.data = conv.weight.data * scale.reshape(-1, *([1] * (conv.weight.dim() - 1)))
            bias = conv.bias.data if conv.bias is not None else torch.zeros_like(bn.running_mean)
            conv.bias = nn.Parameter((bias - bn.running_mean) * scale + bn.bias)
            seq[i + 1] = nn.Identity()
    return m


def _quant_weight(w, bits):
    """Per-output-channel symmetric quantization, returned dequantized."""
    qmax = 2 ** (bits - 1) - 1
    flat = w.reshape(w.shape[0], -1)
    scale = flat.abs().max(dim=1).values.clamp(min=1e-12) / qmax
    scale = scale.reshape(-1, *([1] * (w.dim() - 1)))
    return torch.clamp(torch.round(w / scale), -qmax, qmax) * scale


def _quant_act(x, lo, hi, bits):
    """Per-tensor asymmetric quantization over [lo, hi] (range extended to include 0)."""
    lo, hi = min(lo, 0.0), max(hi, 0.0)
    qmax = 2 ** bits - 1
    scale = max(hi - lo, 1e-12) / qmax
    zp = round(-lo / scale)
    return (torch.clamp(torch.round(x / scale) + zp, 0, qmax) - zp) * scale


class FakeQuant(nn.Module):
    """Simulated inference of a trained model with `bits`-bit weights and `act_bits`-bit
    activations (default: the same as the weights). Call calibrate() before use."""

    def __init__(self, model, bits, act_bits=None):
        super().__init__()
        self.bits = bits
        self.act_bits = bits if act_bits is None else act_bits
        self.net = fold_bn(model)
        self.layers = [m for m in self.net.modules() if isinstance(m, QUANT_LAYERS)]
        for m in self.layers:
            m.weight.data = _quant_weight(m.weight.data, bits)
        self.ranges = {}
        self._calibrating = False
        for m in self.layers:
            m.register_forward_pre_hook(self._hook)

    def _hook(self, module, inputs):
        x = inputs[0]
        if self._calibrating:
            lo, hi = self.ranges.get(module, (np.inf, -np.inf))
            self.ranges[module] = (min(lo, x.min().item()), max(hi, x.max().item()))
            return None
        lo, hi = self.ranges[module]
        return (_quant_act(x, lo, hi, self.act_bits),)

    @torch.no_grad()
    def calibrate(self, X, batch=1024):
        self._calibrating = True
        for i in range(0, len(X), batch):
            self.net(X[i:i + batch])
        self._calibrating = False
        return self

    def forward(self, x):
        return self.net(x)


def _to_half(t):
    return t.half().float()


class Float16Sim(nn.Module):
    """Simulated FP16 inference: BatchNorm folded, weights and biases rounded to half
    precision, every conv/linear layer's input rounded to half precision, accumulation in
    FP32 (as on an FPU with half-precision storage). Needs no calibration."""

    def __init__(self, model):
        super().__init__()
        self.net = fold_bn(model)
        for m in self.net.modules():
            if isinstance(m, QUANT_LAYERS):
                m.weight.data = _to_half(m.weight.data)
                if m.bias is not None:
                    m.bias.data = _to_half(m.bias.data)
                m.register_forward_pre_hook(lambda module, inputs: (_to_half(inputs[0]),))

    def forward(self, x):
        return self.net(x)


class _WeightFQ(nn.Module):
    """Parametrization: per-output-channel symmetric fake quantization, straight-through gradient."""

    def __init__(self, bits):
        super().__init__()
        self.bits = bits

    def forward(self, w):
        return w + (_quant_weight(w.detach(), self.bits) - w).detach()


def _quant_act_t(x, lo, hi, bits):
    """Tensor version of _quant_act (lo, hi are 0-d tensors), straight-through gradient."""
    lo, hi = torch.clamp(lo, max=0.0), torch.clamp(hi, min=0.0)
    qmax = 2 ** bits - 1
    scale = torch.clamp(hi - lo, min=1e-12) / qmax
    zp = torch.round(-lo / scale)
    q = (torch.clamp(torch.round(x / scale) + zp, 0, qmax) - zp) * scale
    return x + (q - x).detach()


class QAT(nn.Module):
    """Quantization-aware fine-tuning of a trained model. Call calibrate() before training."""

    def __init__(self, model, bits=8, momentum=0.9):
        super().__init__()
        self.bits, self.momentum = bits, momentum
        self.net = fold_bn(model).train()
        layers = [m for m in self.net.modules() if isinstance(m, QUANT_LAYERS)]
        self._calibrating = False
        for m in layers:
            parametrize.register_parametrization(m, "weight", _WeightFQ(bits))
            m.register_buffer("act_lo", torch.tensor(np.inf))
            m.register_buffer("act_hi", torch.tensor(-np.inf))
            m.register_forward_pre_hook(self._hook)

    def _hook(self, module, inputs):
        x = inputs[0]
        lo_b, hi_b = x.detach().min(), x.detach().max()
        if self._calibrating:
            module.act_lo.copy_(torch.minimum(module.act_lo, lo_b))
            module.act_hi.copy_(torch.maximum(module.act_hi, hi_b))
            return None
        if self.training:
            m = self.momentum
            module.act_lo.mul_(m).add_((1 - m) * lo_b)
            module.act_hi.mul_(m).add_((1 - m) * hi_b)
        return (_quant_act_t(x, module.act_lo, module.act_hi, self.bits),)

    @torch.no_grad()
    def calibrate(self, X, batch=1024):
        self._calibrating = True
        for i in range(0, len(X), batch):
            self.net(X[i:i + batch])
        self._calibrating = False
        return self

    def forward(self, x):
        return self.net(x)


class OnnxInt8:
    """ONNX Runtime static INT8 model with a predict-like interface."""

    def __init__(self, model, X_calib, n_calib=2000, seed=0):
        import onnx  # noqa: F401  (import errors surface here, not mid-run)
        import onnxruntime as ort
        from onnxruntime.quantization import (CalibrationDataReader, CalibrationMethod, QuantFormat,
                                              QuantType, quantize_static)
        from onnxruntime.quantization.shape_inference import quant_pre_process

        rng = np.random.default_rng(seed)
        idx = rng.choice(len(X_calib), size=min(n_calib, len(X_calib)), replace=False)
        calib = X_calib[idx].numpy().astype(np.float32)

        class Reader(CalibrationDataReader):
            def __init__(self):
                self.it = iter(calib[i:i + 1] for i in range(len(calib)))

            def get_next(self):
                x = next(self.it, None)
                return None if x is None else {"x": x}

        with tempfile.TemporaryDirectory() as d:
            fp32, pre, int8 = (os.path.join(d, n) for n in ("fp32.onnx", "pre.onnx", "int8.onnx"))
            torch.onnx.export(copy.deepcopy(model).eval(), torch.from_numpy(calib[:1]), fp32,
                              input_names=["x"], output_names=["logits"],
                              dynamic_axes={"x": {0: "b"}, "logits": {0: "b"}}, opset_version=17,
                              dynamo=False)
            quant_pre_process(fp32, pre)
            quantize_static(pre, int8, Reader(), quant_format=QuantFormat.QDQ, per_channel=True,
                            activation_type=QuantType.QInt8, weight_type=QuantType.QInt8,
                            calibrate_method=CalibrationMethod.MinMax)
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = torch.get_num_threads()
            self.sess = ort.InferenceSession(int8, opts, providers=["CPUExecutionProvider"])
            self.fp32_sess = ort.InferenceSession(fp32, opts, providers=["CPUExecutionProvider"])

    def __call__(self, x, fp32=False):
        sess = self.fp32_sess if fp32 else self.sess
        return torch.from_numpy(sess.run(None, {"x": x.numpy().astype(np.float32)})[0])
