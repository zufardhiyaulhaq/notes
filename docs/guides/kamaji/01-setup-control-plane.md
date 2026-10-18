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
        - op: replace
          path: ""
          value:
            apiVersion: kubelet.config.k8s.io/v1beta1
            kind: KubeletConfiguration
            authentication:
              x509:
                clientCAFile: /etc/kubernetes/pki/ca.crt
            cgroupDriver: systemd
            clusterDNS:
              - 10.96.0.10
            clusterDomain: cluster.local
            rotateCertificates: true
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
- `configurationJSONPatches` replaces the whole kubelet config that Kamaji generates. Without it, a tenant older than the Kamaji build cannot join workers. See below.

### Why replace the kubelet config

Kamaji writes the tenant's `kube-system/kubelet-config` ConfigMap, and `kubeadm join` copies it to `/var/lib/kubelet/config.yaml` on every worker. Kamaji fills it with **every default of its built-in Kubernetes library**, not of the tenant version. `26.10.3-edge` is built on `k8s.io/kubernetes v1.37.1`, so a `v1.34.12` tenant gets 1.37 defaults, and the 1.34 kubelet refuses to start:

```
FeatureGate KubeletCrashLoopBackOffMax not enabled, CrashLoopBackOff.MaxContainerRestartPeriod must not be set
`imagePullCredentialsVerificationPolicy` must not be set if KubeletEnsureSecretPulledImages feature gate is not enabled
```

`kubeadm join` then waits on `[kubelet-check]` until it times out after 4 minutes. Plain kubeadm does not have this problem: it writes only about 12 fields and lets each kubelet default the rest for its own version. Upstream knows about it ([#1047](https://github.com/clastix/kamaji/issues/1047), [#1062](https://github.com/clastix/kamaji/issues/1062)), and its answer is `configurationJSONPatches`.

The patch goes one step further than kubeadm and keeps only the 5 settings a worker kubelet has no usable default for:

| Field | Why it is needed |
|-|-|
| `authentication.x509.clientCAFile` | The API server calls the kubelet (`logs`, `exec`) with a client certificate signed by this CA |
| `cgroupDriver` | The kubelet default is `cgroupfs`, but containerd on a systemd distro uses `systemd` |
| `clusterDNS`, `clusterDomain` | No default. Pods get them in `/etc/resolv.conf` |
| `rotateCertificates` | The default is `false`. Without it the kubelet client certificate is never renewed |

The kubelet fills in the rest for its own version: anonymous auth off, webhook authentication and authorization on, and healthz on `127.0.0.1:10248`. Workers run no static pods, so `staticPodPath` is not needed.

- `op: replace` with `path: ""` swaps the whole generated document for ours, so none of Kamaji's defaults reach the ConfigMap, also after a future Kamaji upgrade.
- Do not use `op: remove` per field. A `remove` on a field that is not there fails the whole phase, and the fields change between Kamaji builds.
- `clusterDNS` and `clusterDomain` must match `networkProfile`. Change both together. `cgroupDriver` must match the container runtime on the workers (`systemd` for containerd on a systemd distro).
- `resolvConf` is left out on purpose, so `kubeadm join` on the node can detect systemd-resolved.
- Kamaji rewrites `kubelet-config` on every reconcile, so the patch applies as soon as the TCP changes. A manual edit to the ConfigMap is reverted.

Check it after the TCP is applied, with the tenant kubeconfig from the next section:

```bash
kubectl --kubeconfig test-control-plane.kubeconfig -n kube-system get cm kubelet-config \
  -o jsonpath='{.data.kubelet}' | grep -c -E 'maxContainerRestartPeriod|imagePullCredentialsVerificationPolicy|memoryReservationPolicy'
```

Expect `0`. On `26.10.3-edge` the ConfigMap goes from 102 lines to 42.

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
