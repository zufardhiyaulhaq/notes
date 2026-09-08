---
tags:
  - networking
  - cdn
  - storage
---

# Backend object access: use the internal endpoint, not the CDN

A CDN is for last-mile delivery to clients. For server-to-server object access, go straight to object storage over its **internal endpoint**.

<svg viewBox="0 0 680 232" width="100%" role="img" aria-labelledby="cdn-t cdn-d" xmlns="http://www.w3.org/2000/svg" style="max-width:680px;height:auto;margin:1.6rem 0;font-family:'Roboto Mono',ui-monospace,monospace;font-size:11.5px">
  <title id="cdn-t">Backend object access: CDN path versus the storage internal endpoint</title>
  <desc id="cdn-d">Via the CDN, a backend request crosses CDN points of presence and partner ISPs on the public internet and can reroute to another region. Via the object storage internal endpoint, it stays on the provider backbone in-region.</desc>
  <defs>
    <marker id="a" markerWidth="9" markerHeight="9" refX="6.5" refY="3" orient="auto"><path d="M0,0 L6.5,3 L0,6" fill="none" stroke="currentColor" stroke-width="1.3"/></marker>
    <marker id="ab" markerWidth="9" markerHeight="9" refX="6.5" refY="3" orient="auto"><path d="M0,0 L6.5,3 L0,6" fill="none" stroke="#1E3AE0" stroke-width="1.3"/></marker>
  </defs>
  <text x="8" y="15" fill="currentColor" opacity="0.55" letter-spacing="0.08em">VIA CDN · UNCONTROLLED</text>
  <g fill="none" stroke="currentColor" stroke-width="1.2">
    <rect x="8" y="26" width="92" height="48" rx="8"/>
    <rect x="132" y="26" width="72" height="48" rx="8"/>
    <rect x="236" y="26" width="200" height="48" rx="8"/>
    <rect x="468" y="26" width="160" height="48" rx="8"/>
  </g>
  <g fill="currentColor" text-anchor="middle">
    <text x="54" y="54">Backend</text>
    <text x="168" y="54">NAT</text>
    <text x="336" y="46">Partner ISPs / BGP</text>
    <text x="336" y="62" opacity="0.7">public internet</text>
    <text x="548" y="46">CDN PoP</text>
    <text x="548" y="62" opacity="0.7">far region on reroute</text>
  </g>
  <line x1="100" y1="50" x2="128" y2="50" stroke="currentColor" stroke-width="1.3" marker-end="url(#a)"/>
  <g stroke="currentColor" stroke-width="1.3" stroke-dasharray="4 3" marker-end="url(#a)">
    <line x1="204" y1="50" x2="232" y2="50"/>
    <line x1="436" y1="50" x2="464" y2="50"/>
  </g>
  <text x="8" y="139" fill="#1E3AE0" opacity="0.85" letter-spacing="0.08em">VIA INTERNAL ENDPOINT · STABLE</text>
  <rect x="8" y="150" width="92" height="48" rx="8" fill="none" stroke="currentColor" stroke-width="1.2"/>
  <rect x="276" y="150" width="196" height="48" rx="8" fill="none" stroke="#1E3AE0" stroke-width="1.4"/>
  <g text-anchor="middle">
    <text x="54" y="178" fill="currentColor">Backend</text>
    <text x="374" y="172" fill="#1E3AE0">Object storage</text>
    <text x="374" y="188" fill="#1E3AE0" opacity="0.85">internal endpoint</text>
    <text x="374" y="220" fill="currentColor" opacity="0.6">provider backbone · in-region</text>
  </g>
  <line x1="100" y1="174" x2="272" y2="174" stroke="#1E3AE0" stroke-width="1.4" marker-end="url(#ab)"/>
</svg>

## Three addresses for one object

```text
public  (CDN):     https://<cdn-domain>/<object>
public  (storage): https://<bucket>.<region>.aliyuncs.com/<object>
private (storage): https://<bucket>.<region>-internal.aliyuncs.com/<object>
```

(Alibaba Cloud OSS shown. Every cloud has an equivalent private path: AWS S3 via a VPC gateway or interface endpoint, GCS via private access.)

## Why not the CDN for a backend

CDN points of presence sit on partner ISPs and do not all peer with every cloud region. A backend request egresses through the NAT gateway onto the public internet, crosses third-party ISPs routed by BGP the cloud does not control, and only then reaches a CDN PoP. An ISP or BGP fault can reroute it to a PoP in a far region, giving non-deterministic latency plus internet egress cost.

## CDN vs internal endpoint

| Property | Backend to CDN PoP (public) | Backend to internal endpoint (private) |
|---|---|---|
| Network | public internet | provider backbone |
| Path control | partner ISP / BGP, not yours | provider, in-region |
| Peering guarantee | none for every PoP | yes |
| Reroute on ISP or BGP fault | yes, to another ISP or region | no |
| Latency under fault | non-deterministic | stable, intra-region |
| Internet egress cost | billed | none |
| Designed for | client, last-mile delivery | server-to-server object access |

## Rule

Backend-originated object access must not traverse the CDN. Use the storage internal endpoint so the traffic stays on the provider backbone, in-region, with no internet egress.

## Sources

- Alibaba Cloud OSS: [regions and endpoints](https://www.alibabacloud.com/help/en/oss/user-guide/regions-and-endpoints)
- Alibaba Cloud OSS: [internal endpoints of buckets and VIP ranges](https://www.alibabacloud.com/help/en/oss/user-guide/internal-endpoints-of-oss-buckets-and-vip-ranges)
