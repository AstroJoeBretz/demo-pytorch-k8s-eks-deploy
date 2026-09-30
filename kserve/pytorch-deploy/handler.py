"""
Custom TorchServe handler for the toy classifier.

BaseHandler's default preprocess() assumes image bytes (it's built for
the common image-classification case). Our model takes a plain JSON
list of floats, so preprocess/inference/postprocess are all overridden
here instead of relying on defaults.
"""
import json

import torch
from ts.torch_handler.base_handler import BaseHandler


class SimpleClassifierHandler(BaseHandler):
    def preprocess(self, data):
        rows = []
        for item in data:
            body = item.get("body")
            if body is None:
                body = item.get("data")
            if isinstance(body, (bytes, bytearray)):
                body = json.loads(body.decode("utf-8"))
            elif isinstance(body, str):
                body = json.loads(body)

            # Accept either the KServe v1 protocol shape...
            if isinstance(body, dict) and "instances" in body:
                rows.extend(body["instances"])
            # ...or a bare list of feature vectors, for direct testing
            elif isinstance(body, list):
                rows.extend(body)
            else:
                raise ValueError(f"Unrecognized request body: {body!r}")

        return torch.tensor(rows, dtype=torch.float32)

    def inference(self, data, *args, **kwargs):
        with torch.no_grad():
            logits = self.model(data)
            return torch.softmax(logits, dim=1)

    def postprocess(self, data):
        return [
            {
                "predicted_class": int(row.argmax().item()),
                "probabilities": [round(p, 4) for p in row.tolist()],
            }
            for row in data
        ]
