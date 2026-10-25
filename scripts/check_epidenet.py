"""Week-1 check: EpiDeNet's shapes, parameter count and MACs against the paper.

The paper gives no parameter count. Its Table IV gives 2,053,516 MACs per inference
for a 4 x 2048 input, which is the check used here.

Usage: python scripts/check_epidenet.py
"""
import os
import sys

import torch
import torch.nn as nn

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from epidenet import EpiDeNet  # noqa: E402

PAPER_MACS_4x2048 = 2_053_516


def count_macs(model, x):
    """Multiply-accumulates of conv and dense layers, plus one add per output for bias."""
    counts = {"mul": 0, "bias": 0}

    def hook(m, inp, out):
        per_sample = out[0].numel()
        if isinstance(m, nn.Conv2d):
            counts["mul"] += per_sample * (m.in_channels // m.groups) * m.kernel_size[0] * m.kernel_size[1]
        else:
            counts["mul"] += per_sample * m.in_features
        if m.bias is not None:
            counts["bias"] += per_sample

    hs = [m.register_forward_hook(hook) for m in model.modules() if isinstance(m, (nn.Conv2d, nn.Linear))]
    with torch.no_grad():
        model(x)
    for h in hs:
        h.remove()
    return counts["mul"], counts["bias"]


def main():
    model = EpiDeNet().eval()
    n_params = sum(p.numel() for p in model.parameters())
    n_no_bn = sum(p.numel() for m in model.modules() if isinstance(m, (nn.Conv2d, nn.Linear))
                  for p in m.parameters())
    print(f"parameters: {n_params:,} total, {n_no_bn:,} without BatchNorm (deployed, BN folded)")

    for T in (1024, 2048):
        x = torch.zeros(1, 1, 4, T)
        shapes = []
        h = x
        for blk in model.features:
            h = blk(h)
            shapes.append(tuple(h.shape[1:]))
        out = model(x)
        mul, bias = count_macs(model, x)
        print(f"input 4 x {T}: block outputs {shapes} -> logits {tuple(out.shape)}")
        print(f"  MACs {mul:,} (+{bias:,} bias adds = {mul + bias:,})")

    mul, bias = count_macs(model, torch.zeros(1, 1, 4, 2048))
    total = mul + bias
    rel = abs(total - PAPER_MACS_4x2048) / PAPER_MACS_4x2048
    print(f"paper Table IV: {PAPER_MACS_4x2048:,} MACs at 4 x 2048; ours {total:,} "
          f"(difference {total - PAPER_MACS_4x2048:+,}, {rel:.4%})")
    ok = rel < 0.001
    print("MAC check passed" if ok else "MAC check FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
