# Deploy Helm charts at startup

**`experimental.deploy.vcluster.helm` installs Helm charts inside the vcluster at startup.** The virtual cluster bootstraps itself with the operators and add-ons it needs, from public repos, with no post-install step.

This field lives under `experimental`. vcluster flags it as experimental, so breaking changes can land between releases. Pin the chart version and re-test on upgrade.

1. list the charts. Each entry has a `chart` (name, repo, absolute version), a `release` (name, namespace), and optional inline `values`. Version constraints are not allowed, only an exact version.
```yaml
experimental:
  deploy:
    vcluster:
      helm:
        - chart:
            name: cert-manager
            repo: https://charts.jetstack.io
            version: v1.16.2
          release:
            name: cert-manager
            namespace: cert-manager
          values: |-
            crds:
              enabled: true
```
2. apply with Helm.
```
helm upgrade --install my-vcluster vcluster \
  --repo https://charts.loft.sh \
  --version 0.37.2 \
  -n my-vcluster --create-namespace \
  -f values.yaml
```
3. connect and the chart is installed inside the vcluster.
```
$ vcluster connect my-vcluster -n my-vcluster
$ kubectl get pod -n cert-manager
NAME                           READY   STATUS    RESTARTS   AGE
cert-manager-...               1/1     Running   0          90s
cert-manager-cainjector-...    1/1     Running   0          90s
cert-manager-webhook-...       1/1     Running   0          90s
```
4. add more entries to the list for more charts. vcluster installs them in order and reconciles them on each `helm upgrade` of the vcluster itself.

## Manifests

??? example "values.yaml"

    ```yaml
    experimental:
      deploy:
        vcluster:
          helm:
            - chart:
                name: cert-manager
                repo: https://charts.jetstack.io
                version: v1.16.2
              release:
                name: cert-manager
                namespace: cert-manager
              values: |-
                crds:
                  enabled: true
    ```

https://www.vcluster.com/docs/vcluster/configure/vcluster-yaml/experimental/deploy
