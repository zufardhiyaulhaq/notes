# Setup Control Plane

To setup a control plane with Kamaji, you can create TenantControlPlane that control overall Kubernetes control plane lifecycle.

### `TenantControlPlane`

`test-control-plane.yaml`:

```yaml
apiVersion: kamaji.clastix.io/v1alpha1
kind: TenantControlPlane
metadata:
  name: test-control-plane
  namespace: kamaji-system
spec:
  controlPlane:
    deployment: {}
    service:
      serviceType: LoadBalancer
  kubernetes:
    version: v1.34.12
    kubelet:
      configurationJSONPatches:
        - op: remove
          path: /crashLoopBackOff/maxContainerRestartPeriod
        - op: remove
          path: /imagePullCredentialsVerificationPolicy
        - op: remove
          path: /memoryReservationPolicy
  networkProfile: {}
  addons:
    coreDNS: {}
    kubeProxy: {}
    konnectivity: {}
```

- No `dataStore`: the TCP uses the operator's default, `default`, which is the etcd `DataStore` the chart created.
- `controlPlane` is the smallest block Kamaji accepts. `serviceType` has no default. `deployment: {}` must be there even when empty, or Kamaji's defaulting webhook fails with `doc is missing path: "/spec/controlPlane/deployment/replicas"`.
- The defaults fill in 2 control-plane pods (`replicas: 2`), a rolling update with `maxSurge: 100%` and `maxUnavailable: 0`, images from `registry.k8s.io`, and **no resource requests**. Each pod has 4 containers: `kube-apiserver`, `kube-controller-manager`, `kube-scheduler` and `konnectivity-server`.
- `networkProfile: {}` must be there even when empty. The defaults (port `6443`, `podCidr: 10.244.0.0/16`, `serviceCidr: 10.96.0.0/16`, `dnsServiceIPs: [10.96.0.10]`, `clusterDomain: cluster.local`) are only filled in when the block exists. Without it the field stays `null`.
- `addons` are opt-in: an empty `{}` turns each one on with its defaults. `konnectivity: {}` gives the server port `8132` and the agent as a DaemonSet.
- `configurationJSONPatches` removes 3 fields from the kubelet config that Kamaji generates. Without it, a tenant older than the Kamaji build cannot join workers. See below.

### Why patch the kubelet config

Kamaji writes the tenant's `kube-system/kubelet-config` ConfigMap, and `kubeadm join` copies it to `/var/lib/kubelet/config.yaml` on every worker. Kamaji fills it with **every default of its built-in Kubernetes library**, not of the tenant version. `26.10.3-edge` is built on `k8s.io/kubernetes v1.37.1`, so a `v1.34.12` tenant gets 1.37 defaults, and the 1.34 kubelet refuses to start:

```
FeatureGate KubeletCrashLoopBackOffMax not enabled, CrashLoopBackOff.MaxContainerRestartPeriod must not be set
`imagePullCredentialsVerificationPolicy` must not be set if KubeletEnsureSecretPulledImages feature gate is not enabled
```

`kubeadm join` then waits on `[kubelet-check]` until it times out after 4 minutes. Plain kubeadm does not have this problem: it writes only about 12 fields and lets each kubelet default the rest for its own version. Upstream knows about it ([#1047](https://github.com/clastix/kamaji/issues/1047), [#1062](https://github.com/clastix/kamaji/issues/1062)), and its answer is `configurationJSONPatches`.

The patch removes the 3 fields a 1.34 node cannot take:

| Field | Problem on 1.34 |
|-|-|
| `crashLoopBackOff.maxContainerRestartPeriod` | kubelet refuses to start: the `KubeletCrashLoopBackOffMax` gate is off in 1.34 |
| `imagePullCredentialsVerificationPolicy` | kubelet refuses to start: the `KubeletEnsureSecretPulledImages` gate is off in 1.34 |
| `memoryReservationPolicy` | Unknown to 1.34. `kubeadm join` only warns (`strict decoding error`) and drops it. Removed so the join is clean |

- A `remove` fails the whole kubelet phase if the field is not there. The fields change between Kamaji builds, so check these 3 paths again on every Kamaji upgrade.
- Every other 1.37 default stays in the ConfigMap. All of them are known to the 1.34 kubelet.
- `cgroupDriver` is not set, and does not need to be. In 1.34 `KubeletCgroupDriverFromCRI` is GA and always on, so the kubelet asks containerd (2.0 or later) for the driver. With `SystemdCgroup = true` in containerd, that is `systemd`.
- Kamaji rewrites `kubelet-config` on every reconcile, so the patch applies as soon as the TCP changes. A manual edit to the ConfigMap is reverted.

Check it after the TCP is applied, with the tenant kubeconfig from the next section:

```bash
kubectl --kubeconfig test-control-plane.kubeconfig -n kube-system get cm kubelet-config \
  -o jsonpath='{.data.kubelet}' | grep -c -E 'maxContainerRestartPeriod|imagePullCredentialsVerificationPolicy|memoryReservationPolicy'
```

Expect `0`. On `26.10.3-edge` the ConfigMap goes from 102 lines to 98.

```bash
kubectl apply -f test-control-plane.yaml
kubectl -n kamaji-system get tcp      # wait for STATUS=Ready, note the CONTROL-PLANE ENDPOINT
```

```
➜  ~ kubectl -n kamaji-system get tcp
NAME                 VERSION    INSTALLED VERSION   STATUS   CONTROL-PLANE ENDPOINT   KUBECONFIG                            DATASTORE   AGE
test-control-plane   v1.34.12   v1.34.12            Ready    192.168.1.201:6443       test-control-plane-admin-kubeconfig   default     14h

➜  ~ kubectl -n kamaji-system get pod
NAME                                  READY   STATUS    RESTARTS   AGE
kamaji-5c7749d9f9-5wxld               1/1     Running   0          24h
kamaji-etcd-0                         1/1     Running   0          24h
kamaji-etcd-1                         1/1     Running   0          24h
kamaji-etcd-2                         1/1     Running   0          24h
test-control-plane-67cdf579d4-bp8cj   4/4     Running   0          13h
test-control-plane-67cdf579d4-zt5zb   4/4     Running   0          13h
```

When `serviceType: LoadBalancer`, the assigned LoadBalancer IP becomes the `ControlPlaneEndpoint`. The same Service exposes `6443` (kube-apiserver) and `8132` (konnectivity-server). To force a specific IP, set `spec.networkProfile.address` plus your LB controller's annotation (e.g. MetalLB's `metallb.io/loadBalancerIPs`) under `spec.controlPlane.service.additionalMetadata.annotations`. ([kamaji-generic](https://kamaji.clastix.io/getting-started/kamaji-generic/))

### Get the admin kubeconfig

```bash
kubectl -n kamaji-system get secret test-control-plane-admin-kubeconfig \
  -o jsonpath='{.data.admin\.conf}' | base64 -d > test-control-plane.kubeconfig
chmod 600 test-control-plane.kubeconfig

kubectl --kubeconfig test-control-plane.kubeconfig cluster-info
```

The Secret has 2 kubeconfigs: `admin.conf` points at the LoadBalancer endpoint, and `admin.svc` points at the in-cluster Service name, for tools that run inside the Management Cluster.
