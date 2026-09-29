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

# Istio VirtualService header values understand Envoy's %OPERATORS%

Header values in an Istio `VirtualService` are not just static strings. `headers.request.set` and `headers.response.set` understand Envoy's command operators, the same `%XXX%` you use in access logs, so you can stamp connection metadata onto a request without writing an EnvoyFilter.

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

The one gotcha: `%DOWNSTREAM_REMOTE_ADDRESS%` includes the port (`1.2.3.4:54321`). For a client-IP header you almost always want `%DOWNSTREAM_REMOTE_ADDRESS_WITHOUT_PORT%` (`1.2.3.4`).

A few operators that are useful on a request header:

| Operator | Value |
|---|---|
| `%DOWNSTREAM_REMOTE_ADDRESS_WITHOUT_PORT%` | client IP |
| `%DOWNSTREAM_LOCAL_ADDRESS%` | the address the client connected to |
| `%PROTOCOL%` | `HTTP/1.1`, `HTTP/2` |
| `%REQ(header-name)%` | copy another request header |
| `%DOWNSTREAM_PEER_URI_SAN%` | client cert SAN (under mTLS) |
| `%START_TIME(%s)%` | request start time |

Two caveats:

- It is a **subset** of the access-log operators (Envoy's "custom request/response headers" list), not the full set. On a **request** header you only get request-time values, since upstream and response values do not exist yet (put those on `response.set`). Write a literal percent as `%%`.
- `DOWNSTREAM_REMOTE_ADDRESS` is the peer Envoy actually sees. Behind an external L7 load balancer that is the load balancer, not the end user, unless the real client is carried through PROXY protocol or `X-Forwarded-For`.

Docs: Envoy [custom request/response headers](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_conn_man/headers#custom-request-response-headers) (the supported subset) and [access log command operators](https://www.envoyproxy.io/docs/envoy/latest/configuration/observability/access_log/usage#command-operators) (the full `%XXX%` format). Istio: [VirtualService Headers](https://istio.io/latest/docs/reference/config/networking/virtual-service/#Headers).
