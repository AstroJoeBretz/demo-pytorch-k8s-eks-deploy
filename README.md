# PyTorch Model → Docker → Kubernetes → EKS/KServe

A toy PyTorch classifier (2-layer feedforward, 20 input features, 3
classes) used as a learning project for the full deployment path: local
Docker container → local Kubernetes (kind) → cluster operations
(RBAC/storage/ingress) → AWS EKS → KServe on TorchServe.

The model is deliberately boring; the point is the deployment pipeline.

## Layout

| Path | What it is |
|---|---|
| `model/` | Model architecture, training script, FastAPI server (`/health`, `/predict`), trained weights |
| `docker/` | CPU Dockerfile (verified) and GPU Dockerfile (untested) |
| `k8s/base/` | Plain nginx Deployment + Service for practicing on kind |
| `k8s/operations/` | Namespace, PVC, RBAC, Ingress |
| `k8s/eks/` | eksctl cluster config and IAM/IRSA setup |
| `kserve/install/` | KServe Helm values (RawDeployment mode) and smoke-test manifest |
| `kserve/pytorch-deploy/` | TorchServe handler and the final InferenceService |

Each folder has its own README. `CLAUDE.md` records the key design
decisions and current status.

## Quick start (local Docker)

Build from the project root and run:

```bash
docker build -f docker/Dockerfile -t pytorch-toy-classifier .
docker run --rm -p 8000:8000 pytorch-toy-classifier
```

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [4.2, -3.1, 1.5, 2.2, -0.5, 3.1, 0.8, -2.9, 4.0, 1.1, -1.2, 3.5, 2.0, -0.8, 1.9, 2.5, -3.3, 0.4, 1.7, -2.1]}'
```

To retrain the weights (in a venv with `requirements-dev.txt` installed):

```bash
cd model && python train.py
```

## Status

- Verified: CPU Docker image build and run, FastAPI endpoints, local
  TorchServe packaging, `k8s/base/` on a kind cluster.
- Not yet done: EKS cluster creation (costs real money once applied),
  the S3 bucket for the KServe InferenceService, GPU image build.

Placeholders such as `ACCOUNT_ID` and `REPLACE-WITH-YOUR-MODEL-BUCKET`
in `k8s/eks/` and `kserve/` must be replaced with your own values.

## License

MIT, see [LICENSE](LICENSE).
