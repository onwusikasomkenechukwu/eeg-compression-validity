"""Model specifications: the network, its input geometry and its training settings.

  - epidenet (primary): EpiDeNet from its Table I; 4 s windows at 256 Hz; channels per dataset
    (CHB-MIT and Siena: the four temporal bipolar channels; SeizeIT2: the subject's two
    behind-the-ear channels). Training as in src/pipeline.py.
  - ahlawat (secondary): the 1D CNN of Ahlawat (2026, public code `final.py`, class EEGCNN),
    18 bipolar channels, 8 s windows at 128 Hz, trained with his settings (Adam lr 1e-4,
    batch 256, at most 200 epochs, early stopping after 20) but under this plan's splits.
    Two changes from his code: two output logits with softmax instead of one logit with a
    sigmoid (the same model class; it lets every model share the scoring code), and this
    pipeline's preprocessing (causal 0.5-40 Hz band-pass, decimation to 128 Hz, training-set
    standardization) instead of his per-record z-score with gap removal.
"""
from dataclasses import dataclass
from typing import Callable

import torch.nn as nn
import torch.nn.functional as F

from epidenet import EpiDeNet


class AhlawatCNN(nn.Module):
    """Ahlawat's EEGCNN (three Conv1d blocks, global average pooling, three dense layers)."""

    def __init__(self, n_channels=18, n_classes=2):
        super().__init__()
        self.conv1 = nn.Conv1d(n_channels, 64, 3, padding=1)
        self.conv2 = nn.Conv1d(64, 64, 3, padding=1)
        self.conv3 = nn.Conv1d(64, 128, 3, padding=1)
        self.conv4 = nn.Conv1d(128, 128, 3, padding=1)
        self.conv5 = nn.Conv1d(128, 256, 3, padding=1)
        self.conv6 = nn.Conv1d(256, 256, 3, padding=1)
        self.pool = nn.MaxPool1d(2)
        self.fc1 = nn.Linear(256, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, n_classes)

    def forward(self, x):  # x: (B, C, T)
        x = self.pool(F.relu(self.conv2(F.relu(self.conv1(x)))))
        x = self.pool(F.relu(self.conv4(F.relu(self.conv3(x)))))
        x = self.pool(F.relu(self.conv6(F.relu(self.conv5(x)))))
        x = x.mean(dim=-1)
        return self.fc3(F.relu(self.fc2(F.relu(self.fc1(x)))))


@dataclass(frozen=True)
class ModelSpec:
    name: str
    make: Callable[[int], nn.Module]   # n_channels -> model returning (B, 2) logits
    win_s: int                         # window length in seconds
    decim: int                         # input rate = 256 Hz / decim
    layout: str                        # "2d": (B, 1, C, T); "1d": (B, C, T)
    channels: dict                     # dataset name -> channel-set name
    lr: float
    max_epochs: int
    patience: int


SPECS = {
    "epidenet": ModelSpec("epidenet", lambda c: EpiDeNet(n_channels=c), win_s=4, decim=1, layout="2d",
                          channels={"chbmit": "temporal4", "siena": "temporal4", "seizeit2": "bte2"},
                          lr=1e-3, max_epochs=300, patience=10),
    "ahlawat": ModelSpec("ahlawat", lambda c: AhlawatCNN(n_channels=c), win_s=8, decim=2, layout="1d",
                         channels={"chbmit": "bipolar18"}, lr=1e-4, max_epochs=200, patience=20),
}
