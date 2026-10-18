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
  dataStore: default
  controlPlane:
    deployment:
      replicas: 2
      resources:
        apiServer:
          requests:
            cpu: 250m
            memory: 512Mi
        controllerManager:
          requests:
            cpu: 100m
            memory: 256Mi
        scheduler:
          requests:
            cpu: 50m
            memory: 128Mi
    service:
      serviceType: LoadBalancer
  kubernetes:
    version: v1.34.12
    kubelet:
      cgroupfs: systemd
  networkProfile:
    port: 6443
    podCidr: 10.244.0.0/16
    serviceCidr: 10.96.0.0/16
    dnsServiceIPs:
      - 10.96.0.10
  addons:
    coreDNS: {}
    kubeProxy: {}
    konnectivity:
      server:
        port: 8132
```

- `dataStore: default` is the etcd `DataStore` the chart created.
- `replicas: 2` runs 2 control-plane pods. Each pod has 4 containers: `kube-apiserver`, `kube-controller-manager`, `kube-scheduler` and `konnectivity-server`.

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
