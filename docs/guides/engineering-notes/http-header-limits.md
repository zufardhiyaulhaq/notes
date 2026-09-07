---
tags:
  - istio
  - envoy
  - networking
  - security
---

# HTTP request header limits, and how to raise them

Every HTTP proxy and application server caps how many headers a request can carry and how large the whole header block can be. Go over either limit and the request is rejected with `431 Request Header Fields Too Large`, before your application code ever sees it. These limits are on by default. You do not configure them, and you do not notice them until something breaks.

## Two independent limits: size and count

There are two separate axes, and half the implementations only cap one:

- **Size**: total bytes of the header block.
- **Count**: number of headers.

## Defaults are all over the place

Defaults vary widely and none of the common implementations agree (check your own version, these move):

| Implementation | Size limit | Count limit |
|---|---|---|
| Envoy | 60 KiB | 100 |
| nginx | 8 KB x 4 buffers | none |
| Kong (OpenResty/nginx) | inherits nginx | none |
| HAProxy | 16 KB (`tune.bufsize`) | 101 |
| Apache httpd | 8190 B | 100 |
| Tomcat (Spring Boot default) | 8 KB | 100 |
| Jetty | 8 KB | none |
| Netty / Reactor Netty | 8 KB | none |
| Undertow | 1 MB | 200 |
| Go net/http | 1 MB | none (500 from Go 1.27) |

nginx, Jetty, and Netty limit bytes only. Envoy, Apache, Tomcat, HAProxy, and Undertow limit both.

## Why both axes matter

Headers are buffered in full before a routing decision can be made, so the whole header block sits in memory per stream, multiplied by concurrency. That makes headers a direct memory-exhaustion surface, and a byte limit alone does not close it:

- **CVE-2019-9516 (0-Length Headers Leak)**: headers with zero-length names and values cost almost nothing against a byte limit, but each still allocates a map entry. Proof that a size cap cannot stop a count-based attack, and why an explicit count cap exists.
- **CVE-2024-30255 (HTTP/2 CONTINUATION Flood)**: a stream of CONTINUATION frames with headers that are never committed can exhaust CPU and memory.

Go reached the same conclusion: Go 1.27 adds `MaxHeaderValueCount` (default 500) precisely because byte limits cannot stop count-based attacks. Even capped at 64 KB, an attacker can still send roughly 13,000 headers in one request.

## Raise the limit in Istio

Both the size and count live in the Envoy `HttpConnectionManager`. Patch them with an `EnvoyFilter`:

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: increase-header-limits
  namespace: istio-system
spec:
  configPatches:
    - applyTo: NETWORK_FILTER
      match:
        context: ANY
        listener:
          filterChain:
            filter:
              name: "envoy.filters.network.http_connection_manager"
      patch:
        operation: MERGE
        value:
          typed_config:
            "@type": "type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager"
            max_request_headers_kb: 128
            common_http_protocol_options:
              max_headers_count: 200
```

## Raise the limit in Envoy Gateway

Envoy Gateway does not expose the header size or count as a first-class API field yet (tracked in [envoyproxy/gateway#5368](https://github.com/envoyproxy/gateway/issues/5368)). Patch the same `HttpConnectionManager` fields (`max_request_headers_kb` and `common_http_protocol_options.max_headers_count`) with an [`EnvoyPatchPolicy`](https://gateway.envoyproxy.io/docs/tasks/extensibility/envoy-patch-policy/), or with a JSONPatch on the `EnvoyProxy` bootstrap. Enable `EnvoyPatchPolicy` in the `EnvoyGateway` config before it takes effect.

## Rule of thumb

- Raise **size and count together**. They are independent limits.
- Raise them at **every hop that buffers headers**, the gateway and the application server both enforce their own default, so a request can be rejected at two layers. A common target is **128 KB size, 200 count**.
- Drop headers you do not need. Fewer headers is the cheapest fix.

## Sources

- Envoy [HttpConnectionManager](https://www.envoyproxy.io/docs/envoy/latest/api-v3/extensions/filters/network/http_connection_manager/v3/http_connection_manager.proto) (`max_request_headers_kb` default 60 KiB, `max_headers_count` default 100)
- [CVE-2019-9516](https://www.tenable.com/plugins/nessus/128067), [CVE-2024-30255](https://www.sentinelone.com/vulnerability-database/cve-2024-30255/)
- Go: [add `MaxHeaderValueCount`](https://github.com/golang/go/issues/79936)
- Envoy Gateway: [max request header size support](https://github.com/envoyproxy/gateway/issues/5368)
