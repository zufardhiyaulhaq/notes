# vcluster Learning

A **vcluster is a full Kubernetes API server running as a pod inside a namespace of a host cluster.** Workloads you create in it are synced down and scheduled as real pods on the host. You get cluster-level objects (namespaces, CRDs, RBAC, your own API server version) without a second real cluster to pay for and operate.

Everything here uses the official `vcluster` Helm chart from `https://charts.loft.sh`, distro `k8s`, chart version `0.37.2`.

## Learning

1. One values file drives everything. The chart reads `vcluster.yaml` (passed as Helm `-f values.yaml`), so every option below is a block in the same file.
2. Pick the distro once. `controlPlane.distro.k8s.enabled: true` runs vanilla Kubernetes (the default). Only one distro can be enabled at a time.
3. The API server listens on `https://localhost:8443` inside the pod. Anything reaching it under a different hostname needs that hostname in the certificate (`controlPlane.proxy.extraSANs`) and in the exported kubeconfig (`exportKubeConfig.server`).
4. vcluster always writes a kubeconfig secret `vc-<name>` in the host namespace. Set `exportKubeConfig.secret.name` to also write a second one with your own server URL for CI or GitOps.
5. A ResourceQuota only counts pods that declare requests. Enable `policies.limitRange` alongside `policies.resourceQuota` so pods without requests still get defaults and still count.
6. `experimental.deploy` runs manifests and Helm charts inside the vcluster at startup. It is flagged experimental by vcluster: breaking changes can land between releases.
7. The virtual control plane is a single pod by default. Back it with embedded etcd or an external database if you need HA.

## Cheatsheet

### Install or upgrade

```
helm upgrade --install my-vcluster vcluster \
  --repo https://charts.loft.sh \
  --version 0.37.2 \
  -n my-vcluster --create-namespace \
  -f values.yaml
```

### Connect with the CLI

```
vcluster connect my-vcluster -n my-vcluster
kubectl get namespaces
vcluster disconnect
```

### Connect without the CLI (read the exported secret)

```
kubectl -n my-vcluster get secret vc-my-vcluster \
  -o jsonpath='{.data.config}' | base64 -d > kubeconfig.yaml
export KUBECONFIG=$(pwd)/kubeconfig.yaml
kubectl get namespaces
```

### List and delete

```
vcluster list
vcluster delete my-vcluster -n my-vcluster
```

https://www.vcluster.com/docs/vcluster/
https://www.vcluster.com/docs/vcluster/configure/vcluster-yaml/
