"""Benchmark one EpiDeNet training epoch and batch inference on CPU vs an accelerator.

Uses the real fold size from the chb01 pilot (4,180 training windows of 4 x 1024, batch 256)
on random data, so it measures compute only.

Usage: python scripts/bench_device.py --device cpu|cuda|dml [--threads 8] [--epochs 3]
"""
import argparse
import os
import sys
import time

import torch
import torch.nn as nn

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from epidenet import EpiDeNet  # noqa: E402


def get_device(name):
    if name == "dml":
        import torch_directml
        return torch_directml.device()
    return torch.device(name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--n", type=int, default=4180)
    args = ap.parse_args()
    torch.set_num_threads(args.threads)
    dev = get_device(args.device)

    torch.manual_seed(0)
    X = torch.randn(args.n, 1, 4, 1024).to(dev)
    y = torch.randint(0, 2, (args.n,)).to(dev)
    model = EpiDeNet().to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.CrossEntropyLoss()

    times = []
    for _ in range(args.epochs + 1):  # first epoch is warm-up (kernel compilation, allocation)
        t0 = time.perf_counter()
        perm = torch.randperm(args.n)
        model.train()
        for i in range(0, args.n, 256):
            idx = perm[i:i + 256].to(dev)
            opt.zero_grad()
            loss_fn(model(X[idx]), y[idx]).backward()
            opt.step()
        float(loss_fn(model(X[:8]), y[:8]))  # sync
        times.append(time.perf_counter() - t0)

    model.eval()
    Xi = torch.randn(21600, 1, 4, 1024)  # 6 h of 1 s-hop test windows
    t0 = time.perf_counter()
    with torch.no_grad():
        for i in range(0, len(Xi), 2048):
            model(Xi[i:i + 2048].to(dev)).float().cpu()
    t_inf = time.perf_counter() - t0
    print(f"{args.device}: train {sum(times[1:]) / args.epochs:.2f} s/epoch (warm-up {times[0]:.2f} s), "
          f"inference on 21,600 windows {t_inf:.2f} s")


if __name__ == "__main__":
    main()
