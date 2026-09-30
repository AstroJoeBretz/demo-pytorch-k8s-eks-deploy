# EKS Cluster — Step 4

> **Cost warning, read this first:** everything in this file provisions
> real, billable AWS resources - the EKS control plane (~$0.10/hour) plus
> two `m5.large` EC2 instances, plus a NAT gateway eksctl creates by
> default (also billed hourly), plus any EBS volumes or load balancers
> you create along the way. None of the earlier steps (kind, local
> Kubernetes) cost anything - this is the first one that does. **The
> cleanup command at the very bottom of this file is the most important
> command here.** Run it as soon as you're done experimenting for the
> day; don't leave this running overnight by accident.

Prerequisites: `eksctl`, `kubectl`, `aws` CLI installed and configured
(`aws sts get-caller-identity` should return your account details
without error).

## 1. Create the cluster

```bash
eksctl create cluster -f cluster.yaml
```

This takes 15-20 minutes - EKS is provisioning a real control plane,
not a container like kind was. Get a coffee.

```bash
kubectl get nodes
# Should show 2 nodes in Ready status once it's done
```

## 2. Set up IRSA for your model server

Get your account ID and create the S3 policy:

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Edit iam-policy-s3-read.json first - replace the bucket placeholder
# with your actual model bucket name

aws iam create-policy \
  --policy-name model-server-s3-read \
  --policy-document file://iam-policy-s3-read.json
```

Now create the IAM role + Kubernetes ServiceAccount together in one
command - this generates the trust policy shown in
`trust-policy-example.json`, and writes the same annotation shown in
`serviceaccount-irsa.yaml`:

```bash
eksctl create iamserviceaccount \
  --cluster ml-serving-cluster \
  --namespace ml-serving \
  --name model-server-sa \
  --attach-policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/model-server-s3-read \
  --approve
```

Verify the annotation actually landed:

```bash
kubectl get sa model-server-sa -n ml-serving -o yaml
# Look for eks.amazonaws.com/role-arn under annotations
```

Any Pod that sets `serviceAccountName: model-server-sa` can now read
from that one S3 bucket - no access keys anywhere in your image or
environment variables.

## 3. Install the AWS Load Balancer Controller

The controller needs its own IRSA setup first (it calls EC2/ELB APIs
to provision load balancers on your behalf):

```bash
curl -O https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.9.0/docs/install/iam_policy.json

aws iam create-policy \
  --policy-name AWSLoadBalancerControllerIAMPolicy \
  --policy-document file://iam_policy.json

eksctl create iamserviceaccount \
  --cluster ml-serving-cluster \
  --namespace kube-system \
  --name aws-load-balancer-controller \
  --attach-policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/AWSLoadBalancerControllerIAMPolicy \
  --approve
```

Then install the controller itself via Helm:

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=ml-serving-cluster \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller
```

Once this is running, an Ingress with `ingressClassName: alb` (instead
of `nginx`, like step 3 used) provisions a real internet-facing ALB
automatically - no hostPort/extraPortMappings workarounds needed.

## 4. IRSA for the EBS CSI driver

The `aws-ebs-csi-driver` add-on in `cluster.yaml` also needs its own IAM
role to actually create/attach EBS volumes:

```bash
eksctl create iamserviceaccount \
  --cluster ml-serving-cluster \
  --namespace kube-system \
  --name ebs-csi-controller-sa \
  --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy \
  --role-only \
  --role-name AmazonEKS_EBS_CSI_DriverRole \
  --approve

eksctl update addon \
  --cluster ml-serving-cluster \
  --name aws-ebs-csi-driver \
  --service-account-role-arn arn:aws:iam::${ACCOUNT_ID}:role/AmazonEKS_EBS_CSI_DriverRole
```

Once done, the step-3 `pvc.yaml` example (the Redis PVC) will
dynamically provision a real EBS volume instead of relying on kind's
node-local storage stand-in - apply it here the same way you did on
kind, no changes needed to the manifest itself.

## Clean up — DO THIS WHEN YOU'RE DONE

```bash
# Remove the load balancer controller first - if you skip this,
# eksctl may fail to delete the cluster later because a live ALB is
# still attached to the VPC it's trying to tear down
helm uninstall aws-load-balancer-controller -n kube-system

eksctl delete cluster -f cluster.yaml
```

Double-check in the AWS console afterward (EKS, EC2, and VPC pages)
that nothing was left behind - it's rare, but a stuck load balancer or
orphaned EBS volume can survive a cluster deletion and keep billing.
