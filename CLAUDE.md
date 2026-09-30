# PyTorch Model → EKS/KServe Deployment

## What this project is

A toy PyTorch classifier (2-layer feedforward, 20 input features, 3
classes) built up in stages: local Docker container → local Kubernetes
(kind) → cluster operations (RBAC/storage/ingress) → real AWS EKS
cluster → KServe → the model actually packaged and deployed through
KServe on TorchServe.

Nothing here is hypothetical scaffolding - the model was trained, the
FastAPI dev server was hit with real requests, and the TorchServe
package was built and served locally with real predictions, all
verified before being written to disk. What was **not** run: the
Docker build itself (no daemon available while building this), and
nothing has touched a real EKS cluster yet. See "Not yet done" below.

## Directory structure

- `model/` - model architecture, training script, FastAPI dev server.
  Source of truth for the model itself.
- `docker/` - Dockerfile (CPU) + Dockerfile.gpu (untested), containerizes
  `model/`
- `k8s/base/` - Deployment + Service for a local kind cluster
- `k8s/operations/` - Namespace, PVC, RBAC, Ingress (needs an
  ingress-nginx controller installed separately)
- `k8s/eks/` - eksctl ClusterConfig plus the IAM/IRSA setup, for a real
  AWS cluster
- `kserve/install/` - KServe Helm values (RawDeployment mode, no
  Istio/Knative) and an sklearn smoke-test manifest
- `kserve/pytorch-deploy/` - the actual model packaged as a TorchServe
  `.mar`, its custom handler, and the final InferenceService

Each folder has its own README with the specifics for that piece.

## Key decisions worth knowing before changing anything

- **RawDeployment mode, not Serverless** - avoids installing
  Istio/Knative, reuses the nginx Ingress from `k8s/operations/`.
  Trade-off: no scale-to-zero.
- **TorchServe, not a hand-rolled server** - the InferenceService in
  `kserve/pytorch-deploy/` uses KServe's native `pytorch` predictor type
  (v1 protocol), not MLServer.
- **GPU node group is commented out** in `k8s/eks/cluster.yaml`
  (`minSize: 0`) - uncomment it deliberately, it costs money.
- **IRSA, not static AWS keys** - the ServiceAccount referenced in
  `kserve/pytorch-deploy/pytorch-toy-classifier-inferenceservice.yaml`
  (`model-server-sa`) assumes an IAM role via OIDC, set up in
  `k8s/eks/serviceaccount-irsa.yaml`.

## Known duplication to clean up

`torch-model-archiver` needs `model.py` and `model.pt` as local files,
so during development they were hand-copied into
`kserve/pytorch-deploy/`. That copy was deliberately **not** carried
over into this structure - see `kserve/pytorch-deploy/MODEL_SOURCE.md`.
Wire a real build step that pulls both from `model/` instead of
maintaining a second copy that can drift.

## Local Python environment

Anything run outside Docker - `model/train.py`, `model/inference.py`,
or testing the TorchServe packaging in `kserve/pytorch-deploy/` -
should happen inside a venv, not system Python:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

`requirements-dev.txt` at the project root is a superset of
`docker/requirements.txt`: it adds `torch` itself (CPU build) plus
`torchserve` and `torch-model-archiver`, which the container never
needs but local packaging/testing does.

This is unrelated to Docker's own internal venv (see "Key decisions"
above) - that one only exists to keep the final image slim and has
nothing to do with your local machine's isolation.

## Commands that were actually run and verified

```bash
# Train + verify the model (from model/)
python train.py
uvicorn inference:app --host 0.0.0.0 --port 8000 &
curl localhost:8000/health
curl -X POST localhost:8000/predict -H "Content-Type: application/json" -d '{...}'

# Package + locally serve with TorchServe (from kserve/pytorch-deploy/,
# after copying model.py and model_artifacts/model.pt in from model/)
torch-model-archiver --model-name pytorch-toy-classifier --version 1.0 \
  --model-file model.py --serialized-file model.pt --handler handler.py \
  --export-path model-store --force

torchserve --start --ncs --model-store model-store \
  --models pytorch-toy-classifier=model-store/pytorch-toy-classifier.mar \
  --disable-token-auth

curl -X POST http://localhost:8080/predictions/pytorch-toy-classifier \
  -H "Content-Type: application/json" \
  -d '{"instances": [[4.2, -3.1, 1.5, 2.2, -0.5, 3.1, 0.8, -2.9, 4.0, 1.1, -1.2, 3.5, 2.0, -0.8, 1.9, 2.5, -3.3, 0.4, 1.7, -2.1]]}'

torchserve --stop
```

## Not yet done

- `docker/Dockerfile.gpu` is still unbuilt (needs an NVIDIA GPU host).
  The CPU `docker/Dockerfile` was built and run for real: build from the
  project root with `docker build -f docker/Dockerfile .`.
- EKS cluster has never been created - `k8s/eks/cluster.yaml` is
  unapplied. Real AWS cost starts the moment it is.
- The final InferenceService
  (`kserve/pytorch-deploy/pytorch-toy-classifier-inferenceservice.yaml`)
  has a placeholder S3 bucket - needs a real bucket, and the model
  needs uploading there in the exact `model-store/` + `config/` layout
  described in `kserve/pytorch-deploy/README.md`.
- No CI, no automated tests beyond the manual curl checks above.
