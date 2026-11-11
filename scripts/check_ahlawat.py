"""Implementation check for Ahlawat's model (OSF update 2, fidelity check part A).

Loads the EEGCNN class from Ahlawat's own final.py (parsed, not run: the file is a long
script) and compares it with models.AhlawatCNN:
  1. the same layers with the same shapes, apart from the output layer (his: one logit for a
     sigmoid; ours: two logits for a softmax, as registered);
  2. with his weights copied into ours, the same activations up to the output layer, and
     the same seizure probability when ours' two logits are set to (0, his logit);
  3. parameter counts.
The other half of part A, his code reproducing his reported FP32 test AUROC on his split,
is in runs/ahlawat_check/CHECK.md (0.9618 vs 0.9617).

Usage: python scripts/check_ahlawat.py [--final code/brain-inspired-computing/final.py]
"""
import argparse
import ast
import os
import sys

import torch
import torch.nn as nn
import torch.nn.functional as F

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from models import SPECS, AhlawatCNN  # noqa: E402

N_CHANNELS, N_TIME = 18, 8 * 128   # his montage; 8 s at 128 Hz


def load_his_class(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EEGCNN")
    ns = {"nn": nn, "F": F, "torch": torch}
    exec(compile(ast.Module([node], []), path, "exec"), ns)
    return ns["EEGCNN"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--final", default=os.path.join(ROOT, "code", "brain-inspired-computing", "final.py"))
    args = ap.parse_args()
    torch.manual_seed(0)
    his = load_his_class(args.final)(N_CHANNELS).eval()
    ours = SPECS["ahlawat"].make(N_CHANNELS).eval()
    assert isinstance(ours, AhlawatCNN)

    hs, os_ = his.state_dict(), ours.state_dict()
    shared = [k for k in hs if not k.startswith("fc3.")]
    ok = True
    print("layer shapes (his vs ours):")
    for k in hs:
        same = k in os_ and hs[k].shape == os_[k].shape
        print(f"  {k:12s} {tuple(hs[k].shape)!s:16s} {tuple(os_[k].shape) if k in os_ else 'missing'}"
              + ("" if same else "   <- differs" + (" (output layer, as registered)" if k.startswith("fc3.") else "")))
        ok &= same or k.startswith("fc3.")
    extra = [k for k in os_ if k not in hs]
    ok &= not extra
    print(f"layers only in ours: {extra or 'none'}")

    with torch.no_grad():
        ours.load_state_dict({**os_, **{k: hs[k] for k in shared}})
        ours.fc3.weight.copy_(torch.cat([torch.zeros_like(hs["fc3.weight"]), hs["fc3.weight"]]))
        ours.fc3.bias.copy_(torch.cat([torch.zeros_like(hs["fc3.bias"]), hs["fc3.bias"]]))
        x = torch.randn(64, N_CHANNELS, N_TIME)
        p_his = torch.sigmoid(his(x))
        p_ours = torch.softmax(ours(x), 1)[:, 1]
        diff = float((p_his - p_ours).abs().max())
    ok &= diff < 1e-6
    n_his = sum(v.numel() for v in hs.values())
    n_ours = sum(v.numel() for v in os_.values())
    print(f"seizure probability, his weights in both: max abs difference {diff:.2e}")
    print(f"parameters: his {n_his:,}, ours {n_ours:,} (difference {n_ours - n_his}: the second output logit)")
    print("implementation check " + ("passed" if ok else "FAILED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
