# Custom control-plane SAN

**The vcluster API server certificate only lists `localhost` and in-cluster names by default.** Reach the API under any other hostname, for example an ingress or a load balancer at `vcluster.example.com`, and TLS verification fails: the name is not in the certificate. `controlPlane.proxy.extraSANs` signs the cert for that extra name.

1. add the external hostname to the proxy SAN list.
```yaml
controlPlane:
  proxy:
    extraSANs:
      - vcluster.example.com
```
2. apply it with Helm. The control-plane pod restarts and re-issues its certificate with the new SAN.
```
helm upgrade --install my-vcluster vcluster \
  --repo https://charts.loft.sh \
  --version 0.37.2 \
  -n my-vcluster --create-namespace \
  -f values.yaml
```
3. confirm the hostname is in the served certificate.
```
$ echo | openssl s_client -connect vcluster.example.com:443 2>/dev/null \
  | openssl x509 -noout -text | grep -A1 'Subject Alternative Name'
    X509v3 Subject Alternative Name:
        DNS:vcluster.example.com, DNS:localhost, ...
```
4. a client that reaches the API under `vcluster.example.com` now verifies the certificate instead of erroring with `x509: certificate is valid for localhost, not vcluster.example.com`.

This is the certificate half of a custom endpoint. The kubeconfig still points at `localhost:8443` until you also set `exportKubeConfig.server`, covered in the next guide.

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
    ```

https://www.vcluster.com/docs/vcluster/configure/vcluster-yaml/control-plane
