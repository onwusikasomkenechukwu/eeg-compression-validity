"""EEGformer fidelity check A (update 8): the reimplementation against Table I of Busia et al.
(2024). Checks the tensor shape after every stage and the parameter count (50.6 K published),
exports to ONNX, quantizes it with this study's INT8 path and lists which operators see INT8
inputs. Needs no data. Writes <out>/fidelity_check_a.md.

Usage: python scripts/check_eegformer.py --out runs/stage4_eegformer
"""
import argparse
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

import torch  # noqa: E402

from eegformer import EEGformer  # noqa: E402
from quantize import OnnxInt8  # noqa: E402

PUBLISHED_PARAMS = 50_600  # "50.6 K"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "runs", "stage4_eegformer"))
    args = ap.parse_args()
    torch.manual_seed(0)
    m = EEGformer().eval()
    x = torch.randn(64, 4, 2048)
    with torch.no_grad():
        e0 = m.conv0(x)
        e1 = m.conv1(e0)
        out = m(x)
    shapes = [("input", (4, 2048), tuple(x.shape[1:])), ("Conv0", (32, 409), tuple(e0.shape[1:])),
              ("Conv1", (32, 81), tuple(e1.shape[1:])), ("logits", (2,), tuple(out.shape[1:]))]
    n = sum(p.numel() for p in m.parameters())
    per_layer = {name: sum(p.numel() for p in mod.parameters()) for name, mod in m.named_children()}
    per_layer["pos"] = m.pos.numel()
    q = OnnxInt8(m, x, n_calib=64)
    with torch.no_grad():
        export_diff = float((out - q(x, fp32=True)).abs().max())
    ok_shapes = all(want == got for _, want, got in shapes)
    ok_params = abs(n - PUBLISHED_PARAMS) <= 50  # the paper rounds to 0.1 K
    lines = ["# EEGformer fidelity check A (architecture, Table I; registered in update 8)", "",
             "| stage | Table I | this model |", "|---|---|---|"]
    lines += [f"| {s} | {w} | {g} |" for s, w, g in shapes]
    lines += ["", f"Parameters: {n:,} (published 50.6 K): **{'PASS' if ok_params else 'FAIL'}**. "
              f"Shapes: **{'PASS' if ok_shapes else 'FAIL'}** (Table I prints 405 after Conv0; a stride-5 "
              "convolution of 2048 samples gives 409, and both give S = 81).", "",
              "Parameters per layer: " + ", ".join(f"{k} {v:,}" for k, v in per_layer.items() if v), "",
              f"ONNX FP32 export reproduces PyTorch: max |logit difference| {export_diff:.2e}.", "",
              "ONNX Runtime static INT8 (QDQ): nodes per operator that read an INT8-rounded input / float input only. "
              "An INT8 input is not an integer kernel: Conv, MatMul and Gemm run on integers; others may run in "
              "float between quantize and dequantize.", "", "| operator | INT8 input | float input |", "|---|---|---|"]
    lines += [f"| {op} | {c['int8_input']} | {c['float_input']} |" for op, c in sorted(q.quantized_ops.items())]
    lines += ["", f"Check A: **{'PASS' if ok_params and ok_shapes and export_diff < 1e-3 else 'FAIL'}**."]
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "fidelity_check_a.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    sys.exit(0 if ok_params and ok_shapes and export_diff < 1e-3 else 1)


if __name__ == "__main__":
    main()
