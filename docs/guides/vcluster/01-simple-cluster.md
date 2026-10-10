# Simple vcluster

**A minimal vcluster is one Helm release and one three-line values file.** The chart brings up an API server pod in the target namespace; that pod is your virtual cluster.

1. write the values file. `distro.k8s` runs vanilla Kubernetes.
```yaml
controlPlane:
  distro:
    k8s:
      enabled: true
```
2. install the chart into its own namespace.
```
helm upgrade --install my-vcluster vcluster \
  --repo https://charts.loft.sh \
  --version 0.37.2 \
  -n my-vcluster --create-namespace \
  -f values.yaml
```
3. the control-plane pod comes up in the host namespace.
```
$ kubectl -n my-vcluster get pod
NAME               READY   STATUS    RESTARTS   AGE
my-vcluster-0      1/1     Running   0          58s
```
4. vcluster writes a kubeconfig secret `vc-<name>` in the same namespace.
```
$ kubectl -n my-vcluster get secret
NAME               TYPE     DATA   AGE
vc-my-vcluster     Opaque   3      58s
```
5. connect with the CLI. It starts a background proxy and switches your context into the virtual cluster.
```
$ vcluster connect my-vcluster -n my-vcluster
$ kubectl get namespaces
NAME              STATUS   AGE
default           Active   1m
kube-system       Active   1m
```
6. anything you create here is a virtual object. The pods are synced down and scheduled as real pods on the host, renamed under the vcluster's namespace.
7. disconnect to return your context to the host cluster.
```
vcluster disconnect
```
8. without the CLI, read the exported secret and point `KUBECONFIG` at it.
```
kubectl -n my-vcluster get secret vc-my-vcluster \
  -o jsonpath='{.data.config}' | base64 -d > kubeconfig.yaml
export KUBECONFIG=$(pwd)/kubeconfig.yaml
kubectl get namespaces
```

## Manifests

??? example "values.yaml"

    ```yaml
    controlPlane:
      distro:
        k8s:
          enabled: true
    ```

https://www.vcluster.com/docs/vcluster/deploy/basics
https://www.vcluster.com/docs/vcluster/configure/vcluster-yaml/control-plane
