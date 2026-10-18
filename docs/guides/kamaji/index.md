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

## 2. Installing Kamaji



See the [Cheatsheet](#cheatsheet) for the exact commands.


## Cheatsheet

### Create / inspect a tenant control plane

```bash
kubectl apply -f test-control-plane.yaml
kubectl -n kamaji-system get tcp,deploy,pods,svc
kubectl get datastore                      # cluster-scoped; see the 'default' etcd
```

### Get kubeconfig and join a worker

```bash
kubectl -n kamaji-system get secret test-control-plane-admin-kubeconfig \
  -o jsonpath='{.data.admin\.conf}' | base64 -d > test-control-plane.kubeconfig
JOIN_CMD=$(kubeadm --kubeconfig test-control-plane.kubeconfig token create --print-join-command)
sudo $JOIN_CMD
```

### Uninstall

```bash
kubectl delete -f test-control-plane.yaml
helm uninstall kamaji -n kamaji-system
kubectl -n kamaji-system delete pvc --all
kubectl delete crd tenantcontrolplanes.kamaji.clastix.io datastores.kamaji.clastix.io kubeconfiggenerators.kamaji.clastix.io
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
