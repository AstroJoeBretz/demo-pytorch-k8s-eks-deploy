"""
Produces model_artifacts/model.pt.

This is a stand-in for a real training pipeline: it generates synthetic
data with a genuine (if simple) signal in it, then trains just enough
that the model actually learns to separate the classes. The point isn't
the model quality - it's having a real, loadable state_dict to deploy.
"""
import torch
import torch.nn as nn
import torch.optim as optim

from model import SimpleClassifier, INPUT_DIM, NUM_CLASSES

ARTIFACT_PATH = "../model_artifacts/model.pt"


def make_synthetic_data(n_samples: int = 2000):
    """Creates points in `NUM_CLASSES` separated clusters so there's a
    real pattern for the model to learn, rather than pure noise."""
    torch.manual_seed(0)
    centers = torch.randn(NUM_CLASSES, INPUT_DIM) * 4
    labels = torch.randint(0, NUM_CLASSES, (n_samples,))
    X = centers[labels] + torch.randn(n_samples, INPUT_DIM)
    return X, labels


def train():
    X, y = make_synthetic_data()
    model = SimpleClassifier()
    optimizer = optim.Adam(model.parameters(), lr=1e-2)
    loss_fn = nn.CrossEntropyLoss()

    model.train()
    for epoch in range(30):
        optimizer.zero_grad()
        logits = model(X)
        loss = loss_fn(logits, y)
        loss.backward()
        optimizer.step()
        if epoch % 10 == 0 or epoch == 29:
            acc = (logits.argmax(dim=1) == y).float().mean().item()
            print(f"epoch {epoch:2d}  loss={loss.item():.4f}  train_acc={acc:.3f}")

    torch.save(model.state_dict(), ARTIFACT_PATH)
    print(f"Saved weights to {ARTIFACT_PATH}")


if __name__ == "__main__":
    train()
