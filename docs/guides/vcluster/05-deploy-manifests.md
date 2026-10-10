# Deploy manifests at startup

**`experimental.deploy.vcluster.manifests` applies raw YAML inside the vcluster the moment it starts.** The virtual cluster comes up already carrying the objects, no second `kubectl apply` step. This is a bootstrap for things every fresh vcluster needs: a namespace, an operator, a default workload.

This field lives under `experimental`. vcluster flags it as experimental, so breaking changes can land between releases. Pin the chart version and re-test on upgrade.

1. put the raw manifests in a block scalar. Separate documents with `---`, exactly as in a file you would `kubectl apply`.
```yaml
experimental:
  deploy:
    vcluster:
      manifests: |-
        apiVersion: v1
        kind: Namespace
        metadata:
          name: demo
        ---
        apiVersion: apps/v1
        kind: Deployment
        metadata:
          name: nginx
          namespace: demo
        spec:
          replicas: 1
          selector:
            matchLabels:
              app: nginx
          template:
            metadata:
              labels:
                app: nginx
            spec:
              containers:
                - name: nginx
                  image: nginx:1.27
```
2. apply with Helm.
```
helm upgrade --install my-vcluster vcluster \
  --repo https://charts.loft.sh \
  --version 0.37.2 \
  -n my-vcluster --create-namespace \
  -f values.yaml
```
3. connect and the objects are already there.
```
$ vcluster connect my-vcluster -n my-vcluster
$ kubectl get deployment -n demo
NAME    READY   UP-TO-DATE   AVAILABLE   AGE
nginx   1/1     1            1           40s
```
4. vcluster keeps the manifests applied. Edit the block and `helm upgrade` to roll the change into the running vcluster.

## Manifests

??? example "values.yaml"

    ```yaml
    experimental:
      deploy:
        vcluster:
          manifests: |-
            apiVersion: v1
            kind: Namespace
            metadata:
              name: demo
            ---
            apiVersion: apps/v1
            kind: Deployment
            metadata:
              name: nginx
              namespace: demo
            spec:
              replicas: 1
              selector:
                matchLabels:
                  app: nginx
              template:
                metadata:
                  labels:
                    app: nginx
                spec:
                  containers:
                    - name: nginx
                      image: nginx:1.27
    ```

https://www.vcluster.com/docs/vcluster/configure/vcluster-yaml/experimental/deploy
