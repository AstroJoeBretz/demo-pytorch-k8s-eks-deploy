# Kubernetes Basics — Step 2

Prerequisites: kind cluster running (`kind create cluster --name learning`)
and `kubectl` pointed at it (this happens automatically when you create
the cluster).

## Apply both manifests

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

You should see:
```
deployment.apps/nginx-deployment created
service/nginx-service created
```

## Look around

```bash
kubectl get deployments
kubectl get pods
kubectl get services
```

Note the pod names — they're auto-generated with a suffix, like
`nginx-deployment-7f6b9c8d9-x4k2p`. You never name pods directly when
using a Deployment; Kubernetes does it for you.

For more detail on any object:

```bash
kubectl describe deployment nginx-deployment
kubectl describe pod <one-of-the-pod-names>
```

`describe` is your main debugging tool — when something's wrong, this is
where you'll see *why* (image pull errors, failed probes, scheduling
failures, etc. all show up in the Events section at the bottom).

## Reach the service from your machine

`ClusterIP` services aren't exposed outside the cluster by default.
Port-forward to reach one directly for testing:

```bash
kubectl port-forward svc/nginx-service 8080:80
```

Then in another terminal:

```bash
curl http://localhost:8080
```

You should get nginx's default welcome page HTML back.

## Two experiments worth running by hand

**1. Delete a pod and watch it come back.**

```bash
kubectl get pods                      # note one of the pod names
kubectl delete pod <that-pod-name>
kubectl get pods                      # a NEW pod appears within seconds
```

This is the core idea behind Deployments: you declared "2 replicas
should exist," and Kubernetes continuously enforces that — not just at
apply-time, but forever, until you change or delete the Deployment. This
reconciliation loop is the foundation everything else in Kubernetes
(and later, KServe) builds on.

**2. Break the label link on purpose.**

```bash
kubectl get endpoints nginx-service   # shows the pod IPs currently routed to
```

Now edit `service.yaml`, change `app: nginx-demo` to `app: nginx-demo-x`,
and re-apply:

```bash
kubectl apply -f service.yaml
kubectl get endpoints nginx-service   # now empty!
```

The Service still exists, but it has nothing to route to — the selector
no longer matches any pod's labels. This is one of the most common
real-world Kubernetes bugs (a typo in a label), and deliberately causing
it once makes it much faster to recognize later. Revert the change and
re-apply to fix it.

## Clean up

```bash
kubectl delete -f service.yaml
kubectl delete -f deployment.yaml
```

Or delete the whole cluster when you're done experimenting for the day:

```bash
kind delete cluster --name learning
```

(Clusters are cheap to recreate — there's no harm in tearing one down
between sessions.)

## Once your PyTorch image from step 1 is built

You don't need a container registry to use it in kind — you can load a
local image directly into the cluster's node:

```bash
kind load docker-image pytorch-toy-classifier:v1.0 --name learning
```

Then reference it in a Deployment exactly like `nginx-deployment.yaml`
above, but with:

```yaml
image: pytorch-toy-classifier:v1.0
imagePullPolicy: IfNotPresent
```

`imagePullPolicy: IfNotPresent` matters here — without it, Kubernetes
defaults to `Always` for images without a version tag issue, or may try
to pull from a registry instead of using the image you just loaded
locally, and fail since this image doesn't exist anywhere but this
cluster's node.
