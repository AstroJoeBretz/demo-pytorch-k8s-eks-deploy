# Kubernetes Operations — Step 3

Reference manifests for the four remaining step-3 concepts: namespaces,
persistent storage, RBAC, and Ingress. Resource requests/limits,
liveness/readiness probes, and HPA were already covered using the
step-2 nginx example and don't need separate files here.

Assumes the `learning` kind cluster from step 2 still exists
(`kind get clusters` to check, `kind create cluster --name learning`
if not).

## 1. Namespace

```bash
kubectl apply -f namespace.yaml
kubectl get namespaces
```

From here on, either add `-n ml-serving` to every command, or set it as
your default so you don't have to:

```bash
kubectl config set-context --current --namespace=ml-serving
```

## 2. Persistent storage

```bash
kubectl apply -f pvc.yaml
kubectl get pvc -n ml-serving
kubectl get pods -n ml-serving          # redis pod should be Running
```

Prove the data survives a Pod restart:

```bash
# Write a value
kubectl exec -it -n ml-serving deploy/redis -- redis-cli SET hello world

# Kill the pod
kubectl delete pod -n ml-serving -l app=redis

# Wait for the replacement, then check the value is still there
kubectl exec -it -n ml-serving deploy/redis -- redis-cli GET hello
# → "world"
```

If it had used `emptyDir` instead of a PVC, that value would be gone
after the Pod restart — this is the experiment that makes the PV/PVC
distinction concrete.

## 3. RBAC

```bash
kubectl apply -f rbac.yaml
```

Verify permissions directly — this is the debugging command worth
remembering:

```bash
# Can this ServiceAccount read configmaps? (should be "yes")
kubectl auth can-i get configmaps \
  --as=system:serviceaccount:ml-serving:model-server-sa -n ml-serving

# Can it delete pods? (should be "no" - we never granted that)
kubectl auth can-i delete pods \
  --as=system:serviceaccount:ml-serving:model-server-sa -n ml-serving
```

`kubectl auth can-i` is the fastest way to answer "why is this Pod
getting a permissions error" without digging through Role/RoleBinding
YAML by hand.

## 4. Ingress

kind doesn't come with an Ingress controller, so install nginx-ingress
first:

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

# Wait for it to be ready
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s
```

Note: a plain `kind create cluster` doesn't expose ports 80/443 to your
host, so the ingress-nginx pod will run but you likely won't be able to
reach it via `curl model.local` without either recreating the cluster
with `extraPortMappings` (see kind's Ingress guide) or falling back to
`kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 8080:80`
and adding `model.local` to `/etc/hosts` pointing at `127.0.0.1`.

Once that's sorted:

```bash
kubectl apply -f ingress.yaml
kubectl get ingress -n ml-serving

curl -H "Host: model.local" http://localhost:8080/predict
```

This step has the most moving parts of the four — don't be surprised
if it takes a couple of tries to get the networking lined up. That's
normal; Ingress is the piece most people find fiddly on a local cluster
specifically because of this host-port routing, and it gets
meaningfully simpler on EKS (step 4) where the AWS Load Balancer
Controller handles it with a real external IP instead of localhost
tricks.

## Clean up

```bash
kubectl delete namespace ml-serving   # cascades: deletes everything above
kubectl delete -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
```
