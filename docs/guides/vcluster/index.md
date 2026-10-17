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
8. OSS vcluster is controllers, not CRDs. A vcluster is a Helm release of plain objects (StatefulSet + Service + RBAC + Secret); the syncer is the controller, running inside the pod. A CRD that *represents a vcluster* exists only on the vCluster Platform (paid) or via the Cluster API provider (free).

## Creating a vcluster

OSS vcluster has **controllers but no CRDs**: the syncer (inside the control-plane pod) reconciles built-in objects across the virtual and host API servers, so no custom resource type is needed. A CRD that *represents a vcluster* only appears when you add a layer on top.

| Create a vcluster via | CRD? | Cost | Fit |
|-|-|-|-|
| Helm chart / `vcluster create` CLI | No — plain StatefulSet + Service + RBAC + Secret | OSS, free | Default; what ArgoCD deploys |
| vCluster Platform (`VirtualClusterInstance`) | Yes — management-plane CRDs + controller, templates | Free tier; paid at scale | Fleets, multi-tenant management |
| Cluster API provider (`cluster-api-provider-vcluster`) | Yes — vcluster as a CAPI `Cluster` | OSS, free | CRD-driven creation without the Platform |

Deployed through an ArgoCD `Application` pointing at the chart, the declarative/GitOps property comes from Argo tracking that Helm release — not from any vcluster CRD.

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
https://vcluster.com/docs/vcluster/introduction/oss-vs-free
https://github.com/loft-sh/cluster-api-provider-vcluster
