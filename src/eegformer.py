"""EEGformer (Busia et al. 2024, IEEE TBioCAS 18(3):608-621, doi:10.1109/TBCAS.2024.3357509),
reimplemented from its Table I. No public code exists (prereg/SECOND_DETECTOR_EEGFORMER.md).

Input (B, C, W): C = 4 temporal bipolar channels (F7-T7, T7-P7, F8-T8, T8-P8), W = 2048
samples (8 s at 256 Hz). Table I, with K = 5, E = 32, d = 32, H = 8, h = 128:
  Embedding   Conv0  C -> E, kernel K, stride K          (B, E, 409)   [Table I prints 405]
              Conv1  E -> E, kernel K, stride K          (B, E, S=81)
              learned positional encoding, added          (B, S, E)
  Encoder     LayerNorm -> multi-head attention (H heads, q/k/v of size d each) -> + residual
              LayerNorm -> Dense0 (h, GELU) -> Dense1 (E, GELU) -> + residual
              LayerNorm
  Classifier  mean over the S positions -> Dense2 (E -> 2)
50,594 parameters (the paper: 50.6 K).

Read from Table I's layer order, not stated in words, and fixed here:
  - pre-norm encoder (LayerNorm before attention and before the feed-forward network) and a
    final LayerNorm before pooling;
  - GELU after both dense layers of the feed-forward network, as the table lists it;
  - the attention output projection (H*d -> E) is part of multi-head attention, as in Keras;
  - positional encoding initialized at zero (learned; the paper does not give an initializer).
Two attention products (q k^T and the attention-weighted values) are MatMul modules, so the
simulated low-bit and FP16 paths can quantize or round their inputs like a layer's input
(src/quantize.py); in ONNX they export as plain MatMul nodes.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F

from quantize import MatMul


class EEGformer(nn.Module):
    def __init__(self, n_channels=4, n_classes=2, W=2048, K=5, E=32, d=32, H=8, h=128):
        super().__init__()
        self.H, self.d = H, d
        self.conv0 = nn.Conv1d(n_channels, E, K, stride=K)
        self.conv1 = nn.Conv1d(E, E, K, stride=K)
        self.S = ((W - K) // K + 1 - K) // K + 1
        self.pos = nn.Parameter(torch.zeros(1, self.S, E))
        self.ln0 = nn.LayerNorm(E)
        self.qkv = nn.Linear(E, 3 * H * d)
        self.scores = MatMul()
        self.mix = MatMul()
        self.proj = nn.Linear(H * d, E)
        self.ln1 = nn.LayerNorm(E)
        self.ff0 = nn.Linear(E, h)
        self.ff1 = nn.Linear(h, E)
        self.ln2 = nn.LayerNorm(E)
        self.head = nn.Linear(E, n_classes)

    def forward(self, x):  # x: (B, C, W) -> logits (B, n_classes)
        z = self.conv1(self.conv0(x)).transpose(1, 2) + self.pos          # (B, S, E)
        B, S, _ = z.shape
        q, k, v = self.qkv(self.ln0(z)).reshape(B, S, 3, self.H, self.d).permute(2, 0, 3, 1, 4).unbind(0)
        att = torch.softmax(self.scores(q * self.d ** -0.5, k.transpose(-1, -2)), dim=-1)
        a = self.mix(att, v).transpose(1, 2).reshape(B, S, self.H * self.d)
        z = z + self.proj(a)
        z = z + F.gelu(self.ff1(F.gelu(self.ff0(self.ln1(z)))))
        return self.head(self.ln2(z).mean(dim=1))
