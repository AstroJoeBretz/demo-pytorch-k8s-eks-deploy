# KServe — Step 5

Assumes: the EKS cluster from step 4 (or an equivalent cluster) with
the nginx Ingress controller from step 3 already installed, and
`ml-serving` namespace already existing.

Check https://kserve.github.io/website/ for the current release before
running this - the version pinned below (v0.14.1) is accurate as of
when this was written, but confirm before you actually run it.

## 1. Install cert-manager

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.15.3/cert-manager.yaml

kubectl wait --for=condition=Available --timeout=120s \
  -n cert-manager deployment/cert-manager \
  deployment/cert-manager-webhook \
  deployment/cert-manager-cainjector
```

## 2. Install KServe's CRDs, then KServe itself

```bash
helm install kserve-crd oci://ghcr.io/kserve/charts/kserve-crd --version v0.14.1

helm install kserve oci://ghcr.io/kserve/charts/kserve \
  --version v0.14.1 -n kserve --create-namespace \
  -f kserve-values-rawdeployment.yaml
```

Confirm it's running:

```bash
kubectl get pods -n kserve
```

**For understanding, not for running:** the values file sets
`deploymentMode: RawDeployment` through Helm, but under the hood this
is just editing a ConfigMap - the same kind of object from the last
question. You could do it directly instead:

```bash
kubectl patch configmap/inferenceservice-config -n kserve \
  --type=strategic \
  -p '{"data": {"deploy": "{\"defaultDeploymentMode\": \"RawDeployment\"}"}}'
```

Helm is just doing this for you, plus installing everything else.

## 3. Smoke test with the built-in sklearn sample

```bash
kubectl apply -f sklearn-iris-sample.yaml

# Watch until READY is True - this can take a minute or two the first
# time, since the image and model both need to download
kubectl get inferenceservice sklearn-iris -n ml-serving -w
```

Once ready, look at what KServe actually created underneath it - this
is the moment RawDeployment mode's whole appeal becomes concrete:

```bash
kubectl get deployment,service,hpa,ingress -n ml-serving -l serving.kserve.io/inferenceservice=sklearn-iris
```

Test it directly via port-forward (simplest path - skips needing the
Ingress host header sorted out):

```bash
kubectl port-forward -n ml-serving svc/sklearn-iris-predictor 8080:80
```

In another terminal:

```bash
curl -X POST http://localhost:8080/v1/models/sklearn-iris:predict \
  -H "Content-Type: application/json" \
  -d '{"instances": [[6.8, 2.8, 4.8, 1.4], [6.0, 3.4, 4.5, 1.6]]}'
```

You should get back predicted iris classes for both instances.

## 4. Clean up the sample when you're satisfied it works

```bash
kubectl delete -f sklearn-iris-sample.yaml
```

## Next: step 6

`pytorch-inferenceservice-template.yaml` is the same shape, pointed at
your own model on S3 instead of KServe's public GCS bucket, using the
IRSA ServiceAccount from step 4. That's step 6 - replace the bucket
placeholder, upload your step-1 model artifacts to S3 in the layout
TorchServe expects, and apply it the same way you just applied the
sklearn sample.
