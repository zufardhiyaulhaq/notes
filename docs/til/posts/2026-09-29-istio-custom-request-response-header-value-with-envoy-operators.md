---
date: 2026-09-29
authors:
  - zufar
categories:
  - Networking
tags:
  - istio
  - envoy
  - networking
---

# Istio custom request/response header values with Envoy's %OPERATORS%

You can create custom request/response Header in Istio via `VirtualService`. apart from static value, we can use Envoy's command operators on `headers.request.set` and `headers.response.set`. the same `%XXX%` you use in access logs, so you can add connection metadata onto a request without writing an EnvoyFilter.

<!-- more -->

Pass the client's address through as a header:

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: echo
spec:
  hosts:
  - echo.example.com
  http:
  - route:
    - destination:
        host: echo.default.svc.cluster.local
    headers:
      request:
        set:
          X-Real-Client-IP: "%DOWNSTREAM_REMOTE_ADDRESS_WITHOUT_PORT%"
```

A few operators that are useful on a request header:

| Operator | Value |
|---|---|
| `%DOWNSTREAM_REMOTE_ADDRESS_WITHOUT_PORT%` | client IP |
| `%DOWNSTREAM_LOCAL_ADDRESS%` | the address the client connected to |
| `%PROTOCOL%` | `HTTP/1.1`, `HTTP/2` |
| `%REQ(header-name)%` | copy another request header |
| `%DOWNSTREAM_PEER_URI_SAN%` | client cert SAN (under mTLS) |
| `%START_TIME(%s)%` | request start time |

## See it live

Two podinfo backends behind the same gateway: `header-test.zufardhiyaulhaq.com` carries the VirtualService below, `test.zufardhiyaulhaq.com` is plain. podinfo's `/headers` echoes back the request headers it received, so one `curl` shows the difference. Full config is in [community-ops](https://github.com/zufardhiyaulhaq/community-ops/tree/master/clusters/home-lab-kubernetes-01/argocd/namespaces/istio-system/ingress/header-test.zufardhiyaulhaq.com).

The header block on the `header-test` VirtualService:

```yaml
headers:
  request:
    set:
      x-real-client-ip: "%DOWNSTREAM_REMOTE_ADDRESS_WITHOUT_PORT%"
      x-downstream-local-address: "%DOWNSTREAM_LOCAL_ADDRESS%"
      x-request-protocol: "%PROTOCOL%"
      x-client-cert-san: "%DOWNSTREAM_PEER_URI_SAN%"
      x-request-start: "%START_TIME(%s)%"
      x-copied-user-agent: "%REQ(USER-AGENT)%"
  response:
    set:
      x-demo: "istio-envoy-operators"
      x-response-protocol: "%PROTOCOL%"
```

With injection, podinfo sees the extra request headers:

```console
$ curl -s https://header-test.zufardhiyaulhaq.com/headers
{
  ...
  "X-Copied-User-Agent": ["curl/8.7.1"],
  "X-Downstream-Local-Address": ["10.3.8.109:443"],
  "X-Real-Client-Ip": ["104.28.213.128"],
  "X-Request-Protocol": ["HTTP/2"],
  "X-Request-Start": ["1790756874"]
}
```

Plain, it does not:

```console
$ curl -s https://test.zufardhiyaulhaq.com/headers
{
  ...
  "X-Forwarded-For": ["104.28.213.128"],
  "X-Request-Id": ["4e317df5-..."]
}
```

The response headers ride back on the way out:

```console
$ curl -sI https://header-test.zufardhiyaulhaq.com/headers
server: istio-envoy
x-demo: istio-envoy-operators
x-response-protocol: HTTP/2
```

Two things the live output makes obvious:

- `x-client-cert-san` is **absent**. The caller presented no mesh client certificate, so `%DOWNSTREAM_PEER_URI_SAN%` resolved to empty, and Envoy drops a header whose value is empty rather than sending it blank.
- `X-Real-Client-Ip` is `104.28.213.128`, the CDN edge in front of the cluster, not the origin client. `%DOWNSTREAM_REMOTE_ADDRESS%` is the peer Envoy actually sees, so behind a proxy or load balancer it is that hop, and the true client is in `X-Forwarded-For`.


Documentation: 

1. Envoy [custom request/response headers](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_conn_man/headers#custom-request-response-headers)
2. [access log command operators](https://www.envoyproxy.io/docs/envoy/latest/configuration/advanced/substitution_formatter#config-advanced-substitution-operators)
3. Istio: [VirtualService Headers](https://istio.io/latest/docs/reference/config/networking/virtual-service/#Headers).
