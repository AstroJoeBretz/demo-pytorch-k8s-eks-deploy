"""
Model architecture.

Kept separate from training and inference code on purpose: both train.py
and inference.py need to construct the exact same architecture before
loading/saving weights, so this is the single source of truth for it.
"""
import torch.nn as nn

INPUT_DIM = 20
HIDDEN_DIM = 64
NUM_CLASSES = 3


class SimpleClassifier(nn.Module):
    """A small feedforward classifier - deliberately simple.

    The point of this exercise is the deployment pipeline, not the model
    architecture, so this is intentionally boring: two hidden layers,
    ReLU activations, dropout for a touch of regularization.
    """

    def __init__(self, input_dim: int = INPUT_DIM, hidden_dim: int = HIDDEN_DIM,
                 num_classes: int = NUM_CLASSES):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, num_classes),
        )

    def forward(self, x):
        return self.net(x)
