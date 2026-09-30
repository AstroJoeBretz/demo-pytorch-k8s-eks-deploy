# Deploy Your Own PyTorch Model — Step 6

This was tested end-to-end in the sandbox before being handed to you:
the step-1 model was packaged into a real TorchServe `.mar` file,
served locally with actual TorchServe (not just FastAPI), and hit with
real prediction requests. Confirmed output:

```
predicted_class: 0
probabilities: [0.7247, 0.155, 0.1203]
```

Identical to step 1's FastAPI server, for the same input - good
confirmation the model itself doesn't change across serving layers,
only the wrapper around it does.

## Files here

```
model.py          the step-1 model architecture (needed by the archiver)
model.pt          the step-1 trained weights
handler.py        custom TorchServe handler - see note below
config.properties TorchServe config, paths matched to KServe's mount point
pytorch-toy-classifier-inferenceservice.yaml   the final InferenceService
```

## Why a custom handler was necessary

TorchServe ships built-in handlers for common cases (`image_classifier`,
`text_classifier`, `object_detector`) - none of which fit a plain
feature-vector classifier. `handler.py` overrides `preprocess`,
`inference`, and `postprocess` directly. It accepts either the KServe
v1 protocol shape (`{"instances": [[...]]}`) or a bare list - both were
tested locally and work.

## 1. Package the model

```bash
torch-model-archiver \
  --model-name pytorch-toy-classifier \
  --version 1.0 \
  --model-file model.py \
  --serialized-file model.pt \
  --handler handler.py \
  --export-path model-store \
  --force
```

Sanity-check it locally before ever touching Kubernetes - this is the
fastest debugging loop available to you, and it's exactly how the
version in this sandbox was verified:

```bash
torchserve --start --ncs --model-store model-store \
  --models pytorch-toy-classifier=model-store/pytorch-toy-classifier.mar \
  --disable-token-auth

curl -X POST http://localhost:8080/predictions/pytorch-toy-classifier \
  -H "Content-Type: application/json" \
  -d '{"instances": [[4.2, -3.1, 1.5, 2.2, -0.5, 3.1, 0.8, -2.9, 4.0, 1.1, -1.2, 3.5, 2.0, -0.8, 1.9, 2.5, -3.3, 0.4, 1.7, -2.1]]}'

torchserve --stop
```

## 2. Upload to S3 in the layout KServe/TorchServe expects

```bash
aws s3 cp model-store/pytorch-toy-classifier.mar \
  s3://YOUR-BUCKET/pytorch-classifier/v1.0/model-store/pytorch-toy-classifier.mar

aws s3 cp config.properties \
  s3://YOUR-BUCKET/pytorch-classifier/v1.0/config/config.properties
```

Confirm the layout matches exactly:

```bash
aws s3 ls s3://YOUR-BUCKET/pytorch-classifier/v1.0/ --recursive
# pytorch-classifier/v1.0/config/config.properties
# pytorch-classifier/v1.0/model-store/pytorch-toy-classifier.mar
```

## 3. Deploy

Edit `pytorch-toy-classifier-inferenceservice.yaml` - replace the
bucket placeholder with your real bucket path from step 2 - then:

```bash
kubectl apply -f pytorch-toy-classifier-inferenceservice.yaml
kubectl get inferenceservice pytorch-toy-classifier -n ml-serving -w
```

## 4. Test the real endpoint

```bash
kubectl port-forward -n ml-serving svc/pytorch-toy-classifier-predictor 8080:80
```

```bash
curl -X POST http://localhost:8080/v1/models/pytorch-toy-classifier:predict \
  -H "Content-Type: application/json" \
  -d '{"instances": [[4.2, -3.1, 1.5, 2.2, -0.5, 3.1, 0.8, -2.9, 4.0, 1.1, -1.2, 3.5, 2.0, -0.8, 1.9, 2.5, -3.3, 0.4, 1.7, -2.1]]}'
```

Same output you got locally in step 1 - now running on real EKS
infrastructure, behind IRSA-authenticated S3 storage, KServe-managed
autoscaling, and everything else from steps 1-5.

## Layering on the rest

**Autoscaling** - already in the InferenceService's `predictor` spec
(`minReplicas`, `maxReplicas`, `scaleTarget`, `scaleMetric`). Under
RawDeployment mode this is the same HPA mechanism from step 3, just
expressed at the InferenceService level instead of a separate HPA
object.

**GPU** - three changes needed together: uncomment the `gpu-workers`
node group in step 4's `cluster.yaml`, replace the CPU resource limits
in the InferenceService with `nvidia.com/gpu: "1"`, and use a
GPU-enabled TorchServe image (KServe's default `pytorch` predictor type
picks this automatically based on whether GPU resources are requested).

**Observability** - two independent things worth having:
- **CloudWatch Container Insights** - an EKS add-on, gives you pod-level
  CPU/memory/restart metrics with no extra setup
- **Prometheus + Grafana** (via the `kube-prometheus-stack` Helm chart)
  - TorchServe already exposes a `/metrics` endpoint on the
  `metrics_address` port from `config.properties` (8082) - point a
  Prometheus scrape config at it for model-level metrics (inference
  latency, queue time, request counts) that CloudWatch alone won't give
  you.

That closes the loop from step 1's Dockerfile through to a real,
autoscaling, observable model endpoint on EKS.
