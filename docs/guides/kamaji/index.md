# Kamaji Learning

## Learning

1. **Kamaji is a Kubernetes operator** (`artifacthub.io/operator: "true"`, `operatorCapabilities: "full lifecycle"`) — controller + CRDs — not just controllers like OSS vcluster. The binary's operator subcommand is literally `manager` ("Start the Kamaji Kubernetes Operator"). ([charts/kamaji/Chart.yaml](https://github.com/clastix/kamaji/blob/26.10.2-edge/charts/kamaji/Chart.yaml), [cmd/manager/cmd.go](https://github.com/clastix/kamaji/blob/26.10.2-edge/cmd/manager/cmd.go))
2. **The control plane runs as pods, the datastore is decoupled.** `kube-apiserver`/`controller-manager`/`scheduler` run as containers in a tenant `Deployment` in the Management Cluster.
3. etcd (or MySQL/PostgreSQL/NATS) is a *separate* shared backend addressed by a `DataStore` object. ([concepts/datastore](https://kamaji.clastix.io/concepts/datastore/))
3. **Two CRDs, one API group** — `kamaji.clastix.io/v1alpha1`: `TenantControlPlane` (namespaced, short name `tcp`) and `DataStore` (cluster-scoped). A third, `KubeconfigGenerator`, is optional. ([api/v1alpha1/groupversion_info.go](https://github.com/clastix/kamaji/blob/26.10.2-edge/api/v1alpha1/groupversion_info.go))
4. **cert-manager is a hard prerequisite.** Kamaji's validating/mutating webhooks need TLS, and cert-manager issues those certs. Install it before Kamaji. ([getting-started/kamaji-generic](https://kamaji.clastix.io/getting-started/kamaji-generic/))
5. **The chart ships a datastore for you.** The `kamaji` Helm chart depends on the `kamaji-etcd` subchart (`kamaji-etcd.deploy: true`), which deploys a multi-tenant etcd StatefulSet and creates a `DataStore` named `default`. ([charts/kamaji/values.yaml](https://github.com/clastix/kamaji/blob/26.10.2-edge/charts/kamaji/values.yaml))
6. **Upstream, unmodified Kubernetes + kubeadm.** Kamaji uses vanilla images from `registry.k8s.io` and kubeadm phases, so tenant clusters are CNCF-conformant and work with standard tooling. ([concepts](https://kamaji.clastix.io/concepts/))
7. **The operator is configured with CLI flags (plus env via Viper).** The `manager` subcommand binds ~18 flags; `viper.AutomaticEnv()` means each has an env-var equivalent, and `POD_NAMESPACE` / `SERVICE_ACCOUNT` are read from the environment directly. ([cmd/manager/cmd.go](https://github.com/clastix/kamaji/blob/26.10.2-edge/cmd/manager/cmd.go))
8. **Datastore selection is per-TCP, with a default.** A `TenantControlPlane` references a `DataStore` by name (`spec.dataStore`); if omitted it inherits the operator's `--datastore` default (chart value `defaultDatastoreName: default`). You can also pin individual resources to dedicated datastores via `spec.dataStoreOverrides`. ([api/v1alpha1/tenantcontrolplane_types.go](https://github.com/clastix/kamaji/blob/26.10.2-edge/api/v1alpha1/tenantcontrolplane_types.go))
9. **Exposure is a Service type you choose** — `LoadBalancer` (most common), `NodePort`, or `ClusterIP` — optionally fronted by an `Ingress` or Gateway API `Gateway`. The LoadBalancer IP becomes the `ControlPlaneEndpoint` workers join. ([tenantcontrolplane_types.go](https://github.com/clastix/kamaji/blob/26.10.2-edge/api/v1alpha1/tenantcontrolplane_types.go))
10. **No free pinned releases since July 2024.** Open-source artifacts are the rolling `latest` OCI image + `0.0.0+latest` Helm chart, and monthly `YY.M.N-edge` releases (e.g. `26.10.2-edge`). Version-pinned/stable builds are a paid CLASTIX subscription. Pin by `image.tag` + chart version in your own GitOps if you need reproducibility. ([reference/versioning](https://kamaji.clastix.io/reference/versioning/))

## Kamaji vs vcluster

| Dimension | Kamaji | OSS vcluster |
|-|-|-|
| What creates a cluster | **A CRD** — apply a `TenantControlPlane` | **No CRD** — a Helm release of plain objects |
| Operator? | Yes: controller (`manager`) **and** CRDs | Controllers only (the syncer), no creation CRD |
| Control-plane process | Real `kube-apiserver` + `controller-manager` + `scheduler` as separate containers in a `Deployment` | Single pod running a k8s/k3s API server (the "syncer" reconciles objects) |
| Where it runs | Pods in a Management Cluster namespace | Pods in a host-cluster namespace |
| Datastore | **Decoupled & shareable** — etcd/MySQL/PostgreSQL/NATS via a `DataStore` CRD | Embedded (sqlite/etcd) inside the vcluster pod by default |
| Worker nodes | **Real external nodes** that `kubeadm join` the control plane | Usually none — workloads are *synced down* to the host as real pods |
| HA | `spec.controlPlane.deployment.replicas` (default 2) | Single pod by default; HA needs embedded etcd / external DB |
| Conformance | Upstream k8s + kubeadm, CNCF-conformant | Conformant distro, but workloads land on the host |

The key mental model shift: a **vcluster is a virtual API server that reuses the host's nodes**; a **Kamaji tenant cluster is a real cluster whose control plane merely happens to be hosted as pods**, with its own dedicated worker nodes.

## 1. Is Kamaji an operator? Architecture

Yes. Kamaji is "an open source Kubernetes Operator that transforms any Kubernetes cluster into a Management Cluster capable of orchestrating and managing multiple independent Tenant Clusters." ([concepts](https://kamaji.clastix.io/concepts/)) The chart declares `artifacthub.io/operator: "true"` with `operatorCapabilities: "full lifecycle"`. ([Chart.yaml](https://github.com/clastix/kamaji/blob/26.10.2-edge/charts/kamaji/Chart.yaml))

- **The controller** is the `kamaji` controller-manager, started with the `manager` subcommand ("Start the Kamaji Kubernetes Operator"). It runs the `TenantControlPlane`, `DataStore`, `CertificateLifecycle`, telemetry controllers, a "soot" manager, and the admission webhooks, using controller-runtime with leader election ID `kamaji.clastix.io` and a webhook server on port `9443`. ([cmd/manager/cmd.go](https://github.com/clastix/kamaji/blob/26.10.2-edge/cmd/manager/cmd.go))
- **Hosted control plane model:** for each `TenantControlPlane`, Kamaji reconciles a `Deployment` whose pods contain the tenant's `kube-apiserver`, `kube-controller-manager`, and `kube-scheduler` (plus a `konnectivity-server` sidecar when enabled, or a `kine` sidecar when the datastore is SQL/NATS), a `Service` to expose it, and the Secrets/ConfigMaps/kubeconfigs generated via kubeadm phases. These run **in the Management Cluster**, not on tenant machines. ([getting-started/kamaji-generic](https://kamaji.clastix.io/getting-started/kamaji-generic/))
- **etcd / datastore lives outside the control-plane pods.** The default datastore is `kamaji-etcd`, a multi-tenant etcd StatefulSet (3 replicas in the sample output) in the Management Cluster. Many tenants can share one datastore, or you can pool/assign dedicated ones. ([concepts/datastore](https://kamaji.clastix.io/concepts/datastore/))

## 2. Installing Kamaji

**Repo:** `https://clastix.github.io/charts` (`helm repo add clastix https://clastix.github.io/charts`). **Charts:** `clastix/kamaji` (operator, bundles CRDs) and `clastix/kamaji-crds` (CRDs only). **Namespace:** conventionally `kamaji-system`. ([getting-started/kamaji-generic](https://kamaji.clastix.io/getting-started/kamaji-generic/))

Versions as of **2026-10-11**:

| Artifact | Version | Notes |
|-|-|-|
| OCI image `clastix/kamaji` | `26.10.2-edge` (or rolling `latest`) | Latest monthly edge, published 2026-10-05 |
| `clastix/kamaji` chart | `0.0.0+latest` (rolling edge) | Last *free pinned* chart was `1.0.0` (appVersion `v1.0.0`, 2024-06-28) |
| `clastix/kamaji-crds` chart | `0.0.0+latest` | CRDs-only chart for GitOps/two-step installs |
| `clastix/kamaji-etcd` subchart | `0.18.1` (appVersion etcd `3.6.12`) | Chart dependency constraint `>=0.15.0` |
| cert-manager | `v1.18.3` (docs-pinned) | Prerequisite |

> Since July 2024, Clastix Labs no longer publishes version-pinned OSS release artifacts; stable/pinned builds are a paid CLASTIX subscription. The free path is `0.0.0+latest` / `latest` or the monthly `-edge` tags. ([reference/versioning](https://kamaji.clastix.io/reference/versioning/))

**Dependencies:** (1) **cert-manager** for webhook TLS; (2) a **datastore** — the chart deploys `kamaji-etcd` automatically, but you can disable it (`kamaji-etcd.deploy: false`) and point at your own etcd / MySQL / PostgreSQL / NATS via a `DataStore` CRD. The Management Cluster itself should provide a CNI, a CSI StorageClass (for etcd PVCs), and (for the common path) LoadBalancer support. ([kamaji-generic](https://kamaji.clastix.io/getting-started/kamaji-generic/), [values.yaml](https://github.com/clastix/kamaji/blob/26.10.2-edge/charts/kamaji/values.yaml))

See the [Cheatsheet](#cheatsheet) for the exact commands.

## 3. Operator configuration knobs (ALL flags)

From **`cmd/manager/cmd.go` @ `26.10.2-edge`** (authoritative; the docs' [reference/configuration](https://kamaji.clastix.io/reference/configuration/) table lags behind the newer flags). `viper.AutomaticEnv()` is enabled, so every flag also has an uppercased-env equivalent.

| Flag | Default | What it does |
|-|-|-|
| `--metrics-bind-address` | `:8080` | Address the metrics endpoint binds to |
| `--metrics-secure` | `false` | Serve metrics over HTTPS behind a bearer token authorized by the `kamaji-metrics-reader` ClusterRole |
| `--health-probe-bind-address` | `:8081` | Address of the `/healthz` + `/readyz` probe endpoint |
| `--pprof-bind-address` | `""` (off) | Address the pprof profiler binds to |
| `--leader-elect` | `true` | Enable leader election (election ID `kamaji.clastix.io`, namespace = `--pod-namespace`) |
| `--tmp-directory` | `/tmp/kamaji` | Working directory for temporary files |
| `--kine-image` | `rancher/kine:v0.11.10-amd64` | Kine sidecar image, used only for SQL/NATS (kine) datastore drivers |
| `--datastore` | `""` | Default `DataStore` name for TCPs that don't declare one (chart sets `default`) |
| `--migrate-image` | `<repo>/clastix/kamaji:<gitTag>` | Image for the Job launched when a TCP is migrated to another datastore |
| `--max-concurrent-tcp-reconciles` | `1` | Worker count for the TenantControlPlane controller |
| `--pod-namespace` | `$POD_NAMESPACE` | Namespace the operator runs in (needed for migration jobs) |
| `--webhook-service-name` | `kamaji-webhook-service` | Webhook server Service name (needed for migration jobs) |
| `--serviceaccount-name` | `$SERVICE_ACCOUNT` | Operator's ServiceAccount (needed for migration jobs) |
| `--webhook-ca-path` | `/tmp/k8s-webhook-server/serving-certs/ca.crt` | Path to the webhook server CA bundle |
| `--controller-reconcile-timeout` | `30s` | Timeout before the controller abandons external calls (datastore, tenant API) |
| `--cache-resync-period` | `10h` | controller-runtime manager cache resync period |
| `--disable-telemetry` | `false` | Disable anonymous analytics sent to `telemetry.clastix.io` |
| `--certificate-expiration-deadline` | `24h` | Lead time before cert expiry to start renewal (must be ≥ 24h) |
| `--zap-devel`, `--zap-encoder`, `--zap-log-level`, `--zap-stacktrace-level`, `--zap-time-encoding` | zap defaults | Logger configuration (`--zap-devel` ↔ chart `loggingDevel.enable`) |

**Hard-coded (not a flag):** the webhook server port is `9443`. Required flags validated at startup: `--kine-image`, `--migrate-image`, `--tmp-directory`, `--pod-namespace`, `--webhook-service-name`, `--serviceaccount-name`, `--webhook-ca-path`.

**Chart `values.yaml` → flag mapping** (set these instead of raw flags; [values.yaml](https://github.com/clastix/kamaji/blob/26.10.2-edge/charts/kamaji/values.yaml)):

| Chart value | Maps to | Default |
|-|-|-|
| `metricsBindAddress` | `--metrics-bind-address` | `:8080` |
| `healthProbeBindAddress` | `--health-probe-bind-address` | `:8081` |
| `temporaryDirectoryPath` | `--tmp-directory` | `/tmp/kamaji` |
| `defaultDatastoreName` | `--datastore` | `default` |
| `telemetry.disabled` | `--disable-telemetry` | `false` |
| `loggingDevel.enable` | `--zap-devel` | `false` |
| `extraArgs` | appended verbatim | `[]` |
| `certManager.issuerRef` | cert-manager Issuer for the webhook serving cert | `{}` → self-signed `kamaji-selfsigned-issuer` |
| `kamaji-etcd.deploy` | deploy the bundled etcd + `default` DataStore | `true` |
| `image.repository` / `image.tag` | operator image | `clastix/kamaji` / chart appVersion |
| `replicaCount` | operator pod replicas | `1` |
| `kubeconfigGenerator.enabled` | deploy the optional Kubeconfig Generator | `false` |

The operator also ships two sibling subcommands: **`migrate`** (run inside the migration Job — flags `--tenant-control-plane`, `--target-datastore`, `--cleanup-prior-migration`, `--timeout 5m`) and **`kubeconfig-generator`**. ([cmd/migrate/cmd.go](https://github.com/clastix/kamaji/blob/26.10.2-edge/cmd/migrate/cmd.go))

## 4. The CRDs

API group/version: **`kamaji.clastix.io/v1alpha1`**. ([groupversion_info.go](https://github.com/clastix/kamaji/blob/26.10.2-edge/api/v1alpha1/groupversion_info.go))

### `TenantControlPlane` (namespaced, short name `tcp`)

Key `spec` fields ([tenantcontrolplane_types.go](https://github.com/clastix/kamaji/blob/26.10.2-edge/api/v1alpha1/tenantcontrolplane_types.go)):

| Field | Meaning |
|-|-|
| `spec.dataStore` | Name of the `DataStore` to use; empty ⇒ operator default. Live migration allowed only between same-driver datastores |
| `spec.dataStoreSchema` / `spec.dataStoreUsername` | Optional, immutable DB name / user (defaults to `<ns>-<name>`) |
| `spec.dataStoreOverrides[]` | Pin a specific resource kind to a dedicated datastore |
| `spec.controlPlane.deployment.replicas` | Control-plane pod replicas (**default 2**); plus nodeSelector/affinity/tolerations/resources/extraArgs per component |
| `spec.controlPlane.deployment.registrySettings` | Override images/registry (default `registry.k8s.io`, `kube-apiserver`/`kube-controller-manager`/`kube-scheduler`) |
| `spec.controlPlane.service.serviceType` | **`LoadBalancer` / `NodePort` / `ClusterIP`** |
| `spec.controlPlane.ingress` | Optional `Ingress` (className, hostname) to expose the API server |
| `spec.controlPlane.gateway` | Optional Gateway API `Gateway` (parentRefs, hostname) — mutually exclusive with `ingress` |
| `spec.kubernetes.version` | Tenant Kubernetes version (e.g. `v1.32.2`) |
| `spec.kubernetes.kubelet` | kubelet settings: `cgroupfs`, `preferredAddressTypes`, JSON patches |
| `spec.kubernetes.admissionControllers` | Enabled admission plugins (sensible default list) |
| `spec.networkProfile.address` / `port` | Advertised endpoint IP (default port `6443`) |
| `spec.networkProfile.certSANs` | Extra API-server cert SANs (add hostnames here) |
| `spec.networkProfile.serviceCidr` / `serviceCidrs` | Service CIDR(s) (default `10.96.0.0/16`; dual-stack supported) |
| `spec.networkProfile.podCidr` / `podCidrs` | Pod CIDR(s) (default `10.244.0.0/16`) |
| `spec.networkProfile.dnsServiceIPs` | CoreDNS service IP(s) |
| `spec.addons.coreDNS` | Enable CoreDNS in the tenant |
| `spec.addons.kubeProxy` | Enable kube-proxy in the tenant |
| `spec.addons.konnectivity` | Enable the Konnectivity tunnel (server port + agent), needed when workers are on a different network |
| `spec.writePermissions` | `blockCreation`/`blockUpdate`/`blockDeletion` to put the tenant API into read-only modes |

Useful status / print columns: `.status.controlPlaneEndpoint`, `.status.kubeconfig.admin.secretName`, `.status.storage.dataStoreName`. The resource also exposes a `scale` subresource on `spec.controlPlane.deployment.replicas`.

### `DataStore` (cluster-scoped)

Key `spec` fields ([datastore_types.go](https://github.com/clastix/kamaji/blob/26.10.2-edge/api/v1alpha1/datastore_types.go)):

| Field | Meaning |
|-|-|
| `spec.driver` | One of **`etcd` / `MySQL` / `PostgreSQL` / `NATS`** (immutable). Non-etcd drivers go through kine |
| `spec.endpoints[]` | Bare `host:port` endpoints (IPv6 must be bracketed) |
| `spec.basicAuth` | Username/password (inline content or `secretReference`) for non-etcd drivers |
| `spec.tlsConfig` | CA + client certificate/key (inline or `secretReference`); required for etcd |
| `status.usedBy[]`, `status.ready` | Which TCPs use it, and whether it validated |

NATS support is still experimental (multi-tenancy not yet supported there). ([concepts/datastore](https://kamaji.clastix.io/concepts/datastore/)) Full field-by-field reference: [reference/api](https://kamaji.clastix.io/reference/api/).

## 5. Creating a Kubernetes "master" (control plane)

The flow is: **apply a `TenantControlPlane`** → Kamaji reconciles the control-plane `Deployment` + `Service` in the Management Cluster → **read the admin kubeconfig** from the generated Secret → **`kubeadm join`** worker machines against the exposed endpoint → install a CNI. ([kamaji-generic](https://kamaji.clastix.io/getting-started/kamaji-generic/))

### Minimal `TenantControlPlane`

```yaml
apiVersion: kamaji.clastix.io/v1alpha1
kind: TenantControlPlane
metadata:
  name: tenant-00
  namespace: tenants
spec:
  dataStore: default                 # the DataStore created by the chart
  controlPlane:
    deployment:
      replicas: 2                     # HA control plane as pods
    service:
      serviceType: LoadBalancer       # or NodePort / ClusterIP
  kubernetes:
    version: v1.32.2
    kubelet:
      cgroupfs: systemd
    admissionControllers:
      - ResourceQuota
      - LimitRanger
  networkProfile:
    port: 6443
    certSANs:
      - tenant-00.example.com
  addons:
    coreDNS: {}
    kubeProxy: {}
    konnectivity:
      server:
        port: 8132
```

```bash
kubectl create namespace tenants
kubectl -n tenants apply -f tenant-00-tcp.yaml
kubectl -n tenants get tcp    # wait for STATUS=Ready, note the CONTROL-PLANE ENDPOINT
```

When `serviceType: LoadBalancer`, the assigned LoadBalancer IP becomes the `ControlPlaneEndpoint`. To force a specific IP, set `spec.networkProfile.address` plus your LB controller's annotation (e.g. MetalLB's `metallb.io/loadBalancerIPs`) under `spec.controlPlane.service.additionalMetadata.annotations`. ([kamaji-generic](https://kamaji.clastix.io/getting-started/kamaji-generic/))

### Get the admin kubeconfig

```bash
kubectl get secret -n tenants tenant-00-admin-kubeconfig \
  -o jsonpath='{.data.admin\.conf}' | base64 -d > tenant-00.kubeconfig

kubectl --kubeconfig tenant-00.kubeconfig cluster-info
```

### Join worker nodes

Kamaji ships no node provisioner (use Cluster API for declarative nodes); the manual path is plain `kubeadm join`:

```bash
# generate a join command from the tenant control plane
JOIN_CMD=$(kubeadm --kubeconfig tenant-00.kubeconfig token create --print-join-command)

# on each prepared worker (containerd + kubelet + kubeadm installed):
sudo $JOIN_CMD

# then install a CNI into the tenant cluster so nodes go Ready
kubectl --kubeconfig tenant-00.kubeconfig apply -f calico.yaml
```

(Worker prerequisites can be automated with Clastix's `yaki` script; for fully declarative nodes use the [Cluster API provider](https://github.com/clastix/cluster-api-control-plane-provider-kamaji).) ([kamaji-generic](https://kamaji.clastix.io/getting-started/kamaji-generic/))

## Cheatsheet

### Install (prerequisite: cert-manager, then Kamaji + bundled etcd)

```bash
# 1) cert-manager (webhook TLS)
helm repo add jetstack https://charts.jetstack.io
helm repo update
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --version v1.18.3 --set crds.enabled=true

# 2) Kamaji operator (chart bundles CRDs + kamaji-etcd datastore)
helm repo add clastix https://clastix.github.io/charts
helm repo update
helm install kamaji clastix/kamaji \
  --version 0.0.0+latest \
  --namespace kamaji-system --create-namespace \
  --set image.tag=latest

kubectl -n kamaji-system get pods   # expect kamaji-* + kamaji-etcd-0/1/2 Running
```

### Alternative: CRDs first (GitOps / separate CRD management)

```bash
helm install kamaji-crds clastix/kamaji-crds -n kamaji-system --create-namespace --version 0.0.0+latest
helm install kamaji      clastix/kamaji      -n kamaji-system --version 0.0.0+latest
```

### Create / inspect a tenant control plane

```bash
kubectl -n tenants apply -f tenant-00-tcp.yaml
kubectl -n tenants get tcp,deploy,pods,svc
kubectl get datastore                      # cluster-scoped; see the 'default' etcd
```

### Get kubeconfig and join a worker

```bash
kubectl get secret -n tenants tenant-00-admin-kubeconfig \
  -o jsonpath='{.data.admin\.conf}' | base64 -d > tenant-00.kubeconfig
JOIN_CMD=$(kubeadm --kubeconfig tenant-00.kubeconfig token create --print-join-command)
sudo $JOIN_CMD
```

### Uninstall

```bash
kubectl delete -f tenant-00-tcp.yaml
helm uninstall kamaji -n kamaji-system
kubectl -n kamaji-system delete pvc --all
kubectl delete crd tenantcontrolplanes.kamaji.clastix.io datastores.kamaji.clastix.io
```

---

Primary sources (repo pinned at tag `26.10.2-edge`, docs read 2026-10-11):

https://github.com/clastix/kamaji

https://kamaji.clastix.io/concepts/

https://kamaji.clastix.io/concepts/datastore/

https://kamaji.clastix.io/getting-started/kamaji-generic/

https://kamaji.clastix.io/reference/configuration/

https://kamaji.clastix.io/reference/versioning/

https://kamaji.clastix.io/reference/api/

https://github.com/clastix/kamaji/blob/26.10.2-edge/cmd/manager/cmd.go

https://github.com/clastix/kamaji/blob/26.10.2-edge/cmd/migrate/cmd.go

https://github.com/clastix/kamaji/blob/26.10.2-edge/api/v1alpha1/tenantcontrolplane_types.go

https://github.com/clastix/kamaji/blob/26.10.2-edge/api/v1alpha1/datastore_types.go

https://github.com/clastix/kamaji/blob/26.10.2-edge/api/v1alpha1/groupversion_info.go

https://github.com/clastix/kamaji/blob/26.10.2-edge/charts/kamaji/Chart.yaml

https://github.com/clastix/kamaji/blob/26.10.2-edge/charts/kamaji/values.yaml

https://clastix.github.io/charts

https://github.com/clastix/kamaji-etcd
