"""EpiDeNet (Ingolfsson et al. 2023, arXiv 2309.07135), reimplemented from its Table I.

Input (B, 1, C, T): C EEG channels (4 temporal channels in the paper), T samples
(1024 = 4 s at 256 Hz on CHB-MIT; 2048 = 8 s in the deployment table).

Table I, as read from the paper (kernel = (channels, time)):
  1  Conv2D  4 filters (1, 4)    -> (4,  C,    T)       MaxPool (1, 8) -> (4,  C,    T//8)
  2  Conv2D 16 filters (1, 16)   -> (16, C,    T//8)    MaxPool (1, 4) -> (16, C,    T//32)
  3  Conv2D 16 filters (1, 8)    -> (16, C,    T//32)   MaxPool (1, 4) -> (16, C,    T//128)
  4  Conv2D 16 filters (16, 1)   -> (16, C,    T//128)  MaxPool (4, 1) -> (16, C//4, T//128)
  5  Conv2D 16 filters (8, 1)    -> (16, C//4, T//128)  AdaptiveAvgPool -> (16, 1, 1)
  6  Dense -> 2

Not stated in the paper, so chosen here and to be stated in the pre-registration:
  - "same" padding (the output shapes keep C and T through every convolution);
  - BatchNorm + ReLU after each convolution (BN folds into the conv at deployment,
    so it adds no MACs);
  - block 5's kernel is read as (8, 1); the table's layout leaves it ambiguous with
    (1, 8), which has the same MAC count.
  - For fewer than 4 channels (SeizeIT2's 2 behind-the-ear channels), block 4's channel
    pooling covers all C channels, so the output is still (16, 1, T//128). With 4 channels
    the network is exactly Table I.
"""
import torch
import torch.nn as nn


def _block(c_in, c_out, kernel, pool=None):
    layers = [
        nn.Conv2d(c_in, c_out, kernel, padding="same"),
        nn.BatchNorm2d(c_out),
        nn.ReLU(),
    ]
    if pool is not None:
        layers.append(nn.MaxPool2d(pool))
    return nn.Sequential(*layers)


class EpiDeNet(nn.Module):
    def __init__(self, n_classes: int = 2, n_channels: int = 4):
        super().__init__()
        self.features = nn.Sequential(
            _block(1, 4, (1, 4), pool=(1, 8)),
            _block(4, 16, (1, 16), pool=(1, 4)),
            _block(16, 16, (1, 8), pool=(1, 4)),
            _block(16, 16, (16, 1), pool=(min(4, n_channels), 1)),
            _block(16, 16, (8, 1)),
            nn.AdaptiveAvgPool2d(1),
        )
        self.classifier = nn.Linear(16, n_classes)

    def forward(self, x):
        # x: (B, 1, C, T) -> logits (B, n_classes)
        return self.classifier(self.features(x).flatten(1))
