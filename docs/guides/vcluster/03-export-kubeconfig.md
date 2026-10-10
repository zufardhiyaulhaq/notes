# Export kubeconfig to a Secret

**vcluster always writes a kubeconfig to a secret `vc-<name>`, but its server URL is the in-cluster address, useless from outside.** `exportKubeConfig` writes a second secret whose server URL is the external hostname, so CI, Argo CD, or another cluster can consume the vcluster directly from a Secret.

1. set the external server URL and the secret name. Pair this with the SAN from the previous guide so the cert matches the URL.
```yaml
controlPlane:
  proxy:
    extraSANs:
      - vcluster.example.com
exportKubeConfig:
  server: https://vcluster.example.com:443
  secret:
    name: my-vcluster-kubeconfig
```
2. apply with Helm.
```
helm upgrade --install my-vcluster vcluster \
  --repo https://charts.loft.sh \
  --version 0.37.2 \
  -n my-vcluster --create-namespace \
  -f values.yaml
```
3. the named secret appears in the host namespace, next to the default `vc-<name>` one.
```
$ kubectl -n my-vcluster get secret
NAME                     TYPE     DATA   AGE
vc-my-vcluster           Opaque   3      2m
my-vcluster-kubeconfig   Opaque   1      2m
```
4. its `config` key is a ready-to-use kubeconfig pointing at the external URL.
```
$ kubectl -n my-vcluster get secret my-vcluster-kubeconfig \
  -o jsonpath='{.data.config}' | base64 -d | grep server
    server: https://vcluster.example.com:443
```
5. consume it from anywhere that can read the secret.
```
kubectl -n my-vcluster get secret my-vcluster-kubeconfig \
  -o jsonpath='{.data.config}' | base64 -d > kubeconfig.yaml
export KUBECONFIG=$(pwd)/kubeconfig.yaml
kubectl get namespaces
```

Set `exportKubeConfig.secret.namespace` to write the secret into a different namespace. vcluster then needs access to that namespace.

## Manifests

??? example "values.yaml"

    ```yaml
    controlPlane:
      distro:
        k8s:
          enabled: true
      proxy:
        extraSANs:
          - vcluster.example.com
    exportKubeConfig:
      server: https://vcluster.example.com:443
      secret:
        name: my-vcluster-kubeconfig
    ```

https://www.vcluster.com/docs/vcluster/configure/vcluster-yaml/export-kube-config
