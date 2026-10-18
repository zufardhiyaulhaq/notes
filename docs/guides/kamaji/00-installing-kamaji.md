# Installing Kamaji

**Repo:** `https://clastix.github.io/charts` (`helm repo add clastix https://clastix.github.io/charts`). **Charts:** `clastix/kamaji` (operator, bundles CRDs) and `clastix/kamaji-crds` (CRDs only). **Namespace:** conventionally `kamaji-system`. ([getting-started/kamaji-generic](https://kamaji.clastix.io/getting-started/kamaji-generic/))

Versions as of **2026-10-17**:

| Artifact | Version | Notes |
|-|-|-|
| OCI image `clastix/kamaji` | `26.10.3-edge`, pinned by digest | Latest monthly edge, published 2026-10-12 |
| `clastix/kamaji` chart | `0.0.0+latest` (rolling edge) | Last *free pinned* chart was `1.0.0` (appVersion `v1.0.0`, 2024-06-28) |
| `clastix/kamaji-crds` chart | `0.0.0+latest` | CRDs-only chart for GitOps/two-step installs |
| `clastix/kamaji-etcd` subchart | `0.18.1`, etcd image pinned to `v3.6.12` | Bundled by today's rolling chart |
| cert-manager | `v1.21.2` | Prerequisite |

> Since July 2024, Clastix Labs no longer publishes version-pinned OSS release artifacts; stable/pinned builds are a paid CLASTIX subscription. The free path is `0.0.0+latest` / `latest` or the monthly `-edge` tags. ([reference/versioning](https://kamaji.clastix.io/reference/versioning/))

**Dependencies:** (1) **cert-manager** for webhook TLS; (2) a **datastore** — the chart deploys `kamaji-etcd` automatically, but you can disable it (`kamaji-etcd.deploy: false`) and point at your own etcd / MySQL / PostgreSQL / NATS via a `DataStore` CRD. The Management Cluster itself should provide a CNI, a CSI StorageClass (for etcd PVCs), and (for the common path) LoadBalancer support. ([kamaji-generic](https://kamaji.clastix.io/getting-started/kamaji-generic/), [values.yaml](https://github.com/clastix/kamaji/blob/26.10.2-edge/charts/kamaji/values.yaml))

### 1) Install cert-manager

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --version v1.21.2 \
  --set crds.enabled=true \
  --set crds.keep=true
```

`crds.keep=true` keeps the cert-manager CRDs, and so every `Certificate`, when the release is removed.

### 2) Install Kamaji

The chart is rolling, so `--version 0.0.0+latest` gives different content over time. Pin every image in your values instead. `kamaji-values.yaml`:

```yaml
image:
  repository: clastix/kamaji
  tag: 26.10.3-edge@sha256:d21c58f391d7a0a312cfe4df096169f6112c569eb0bef4142e3811c682941456
  pullPolicy: IfNotPresent

telemetry:
  disabled: true

gatewayAPI:
  enabled: false

extraArgs:
  - --migrate-image=docker.io/clastix/kamaji:26.10.3-edge@sha256:d21c58f391d7a0a312cfe4df096169f6112c569eb0bef4142e3811c682941456
  - --kine-image=rancher/kine:v0.11.10-amd64

kamaji-etcd:
  image:
    repository: quay.io/coreos/etcd
    tag: v3.6.12
  jobs:
    kubectl:
      image: clastix/kubectl
      tag: v1.33
    etcd:
      image: quay.io/coreos/etcd
      tag: v3.5.6
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      memory: 1Gi
  persistentVolumeClaim:
    size: 8Gi
    storageClassName: nfs-csi
```

| Value | Why |
|-|-|
| `image.tag` with a digest | The chart content and the `latest` tag both move. The digest is the only thing that does not |
| `telemetry.disabled` | By default the operator sends analytics to `telemetry.clastix.io` |
| `gatewayAPI.enabled: false` | The rolling chart has this value. When on, it adds `--enable-gateway-api`, a flag the `26.10.3-edge` binary does not have, so the operator would not start |
| `--migrate-image` | The chart has no value for it. Without it, the binary builds the image name from its own tag. Use the same digest |
| `--kine-image` | Used only by SQL and NATS datastores. Pinned so a chart change cannot move it |
| `kamaji-etcd.image.tag` | etcd itself. `v3.6.12` is what kamaji-etcd `0.18.1` ships |
| `kamaji-etcd.jobs` | The etcd setup Job. By default the kubectl tag follows the cluster's Kubernetes version |
| `kamaji-etcd.resources` | The chart sets no etcd requests |
| `kamaji-etcd.persistentVolumeClaim` | 3 etcd replicas, 8Gi each. Change `storageClassName` to your StorageClass |

```bash
helm repo add clastix https://clastix.github.io/charts
helm repo update
helm install kamaji clastix/kamaji \
  --version 0.0.0+latest \
  --namespace kamaji-system --create-namespace \
  -f kamaji-values.yaml

kubectl -n kamaji-system get pods        # expect kamaji-* and kamaji-etcd-0/1/2 Running
kubectl get datastore                    # expect 'default', READY true
```

### Alternative: CRDs first (GitOps / separate CRD management)

```bash
helm install kamaji-crds clastix/kamaji-crds -n kamaji-system --create-namespace --version 0.0.0+latest
helm install kamaji      clastix/kamaji      -n kamaji-system --version 0.0.0+latest -f kamaji-values.yaml
```