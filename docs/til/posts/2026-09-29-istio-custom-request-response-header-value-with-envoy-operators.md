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


Docs: 
1. Envoy [custom request/response headers](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_conn_man/headers#custom-request-response-headers)
2. [access log command operators](https://www.envoyproxy.io/docs/envoy/latest/configuration/advanced/substitution_formatter#config-advanced-substitution-operators)
3. Istio: [VirtualService Headers](https://istio.io/latest/docs/reference/config/networking/virtual-service/#Headers).
