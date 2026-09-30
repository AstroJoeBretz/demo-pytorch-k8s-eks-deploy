"""
Inference server.

Two endpoints on purpose:
  - /health   liveness/readiness probes will hit this once we're in
              Kubernetes (step 3 of the learning plan) - it should be
              cheap and never touch the model.
  - /predict  the actual inference path.

Loading the model once at startup (not per-request) matters: reloading
weights on every call would make latency and throughput terrible.
"""
import os

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, conlist

from model import SimpleClassifier, INPUT_DIM

MODEL_PATH = os.environ.get("MODEL_PATH", "/app/model_artifacts/model.pt")

app = FastAPI(title="PyTorch Toy Classifier")

model: SimpleClassifier | None = None


@app.on_event("startup")
def load_model():
    global model
    m = SimpleClassifier()
    state_dict = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
    m.load_state_dict(state_dict)
    m.eval()  # disables dropout - required for consistent inference output
    model = m
    print(f"Loaded model from {MODEL_PATH}")


class PredictRequest(BaseModel):
    # enforces exactly INPUT_DIM floats - a malformed request fails
    # validation before it ever reaches the model
    features: conlist(float, min_length=INPUT_DIM, max_length=INPUT_DIM)


class PredictResponse(BaseModel):
    predicted_class: int
    probabilities: list[float]


@app.get("/health")
def health():
    """Cheap liveness/readiness check - no model inference here."""
    return {"status": "ok", "model_loaded": model is not None}


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")

    x = torch.tensor([request.features], dtype=torch.float32)
    with torch.no_grad():
        logits = model(x)
        probs = torch.softmax(logits, dim=1)[0]

    return PredictResponse(
        predicted_class=int(probs.argmax().item()),
        probabilities=[round(p, 4) for p in probs.tolist()],
    )
