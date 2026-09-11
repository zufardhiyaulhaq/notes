---
date: 2026-09-10
authors:
  - zufar
categories:
  - Networking
tags:
  - alibaba-cloud
  - privatelink
  - networking
---

# Alibaba PrivateLink failover watches the endpoint ENI, not your NLB

On Alibaba Cloud PrivateLink, take the NLB out of one zone and the endpoint in the other account can keep sending traffic into that dead zone. The endpoint's DNS record for the zone is not pulled, and the traffic blackholes.

<!-- more -->

Two objects, and where each lives:

- **NLB and endpoint service, same account.** The endpoint service is built on the NLB and follows its zones. Say the NLB runs in zones B and C.
- **Endpoint, a different account.** It connects to the endpoint service across zones B and C, and gets one ENI, one IP, per zone. Its default domain resolves to both:

```
$ nslookup <endpoint-domain>
ep-xxxx.epsrv-xxxx.<region>.privatelink.aliyuncs.com
Address: 10.0.11.11   # zone B endpoint ENI
Address: 10.0.12.6    # zone C endpoint ENI
```

Now zone B is taken out of the NLB on the endpoint-service account. In the case I saw, a network ACL blocked the zone. The NLB stops answering in zone B.

The endpoint account sees no change. PrivateLink runs managed failover on the endpoint by probing each zone's endpoint ENI IP and pulling that zone's DNS record when the IP goes bad (Alibaba docs, below). But the endpoint ENI in zone B is the endpoint account's own interface, and it is still up. So the zone B record stays. The endpoint still reads Connected. Clients keep resolving both IPs, about half pick zone B, reach a healthy ENI, and die one hop later at an NLB that is gone. A blackhole the endpoint account cannot see from the endpoint.

<svg viewBox="0 0 700 248" width="100%" role="img" aria-labelledby="pl-t pl-d" xmlns="http://www.w3.org/2000/svg" style="max-width:700px;height:auto;margin:1.6rem 0;font-family:'Roboto Mono',ui-monospace,monospace;font-size:11.5px">
  <title id="pl-t">PrivateLink blackhole when an NLB zone is removed</title>
  <desc id="pl-d">The client resolves the endpoint to one IP per zone. The zone C path stays healthy through the endpoint ENI to the NLB. On the zone B path the endpoint ENI is still healthy, so its DNS record is kept, but the NLB in zone B was removed, so traffic dies at the account boundary.</desc>
  <defs>
    <marker id="pa" markerWidth="9" markerHeight="9" refX="6.5" refY="3" orient="auto"><path d="M0,0 L6.5,3 L0,6" fill="none" stroke="currentColor" stroke-width="1.3"/></marker>
    <marker id="pab" markerWidth="9" markerHeight="9" refX="6.5" refY="3" orient="auto"><path d="M0,0 L6.5,3 L0,6" fill="none" stroke="#1E3AE0" stroke-width="1.3"/></marker>
  </defs>
  <text x="176" y="15" fill="currentColor" opacity="0.55" letter-spacing="0.06em">ENDPOINT ACCOUNT</text>
  <text x="458" y="15" fill="currentColor" opacity="0.55" letter-spacing="0.06em">ENDPOINT-SERVICE ACCOUNT</text>
  <line x1="416" y1="26" x2="416" y2="224" stroke="currentColor" stroke-width="1" stroke-dasharray="3 3" opacity="0.3"/>
  <rect x="8" y="96" width="92" height="48" rx="8" fill="none" stroke="currentColor" stroke-width="1.2"/>
  <text x="54" y="118" fill="currentColor" text-anchor="middle">Client</text>
  <text x="54" y="134" fill="currentColor" text-anchor="middle" opacity="0.7">2 zone IPs</text>
  <rect x="176" y="30" width="150" height="48" rx="8" fill="none" stroke="currentColor" stroke-width="1.2"/>
  <rect x="466" y="30" width="150" height="48" rx="8" fill="none" stroke="#1E3AE0" stroke-width="1.3"/>
  <g text-anchor="middle">
    <text x="251" y="50" fill="currentColor">Endpoint ENI</text>
    <text x="251" y="66" fill="currentColor" opacity="0.7">zone C</text>
    <text x="541" y="50" fill="#1E3AE0">NLB</text>
    <text x="541" y="66" fill="#1E3AE0" opacity="0.8">zone C</text>
  </g>
  <line x1="100" y1="112" x2="172" y2="58" stroke="currentColor" stroke-width="1.2" marker-end="url(#pa)"/>
  <line x1="326" y1="54" x2="462" y2="54" stroke="#1E3AE0" stroke-width="1.4" marker-end="url(#pab)"/>
  <rect x="176" y="170" width="150" height="48" rx="8" fill="none" stroke="currentColor" stroke-width="1.2"/>
  <rect x="466" y="170" width="150" height="48" rx="8" fill="none" stroke="currentColor" stroke-width="1.2" stroke-dasharray="4 3" opacity="0.5"/>
  <g text-anchor="middle">
    <text x="251" y="190" fill="currentColor">Endpoint ENI</text>
    <text x="251" y="206" fill="currentColor" opacity="0.7">zone B (still up)</text>
    <text x="541" y="190" fill="currentColor" opacity="0.55">NLB zone B</text>
    <text x="541" y="206" fill="currentColor" opacity="0.55">removed</text>
  </g>
  <line x1="100" y1="128" x2="172" y2="190" stroke="currentColor" stroke-width="1.2" marker-end="url(#pa)"/>
  <line x1="326" y1="194" x2="404" y2="194" stroke="currentColor" stroke-width="1.3"/>
  <circle cx="416" cy="194" r="9" fill="none" stroke="currentColor" stroke-width="1.3"/>
  <line x1="410" y1="188" x2="422" y2="200" stroke="currentColor" stroke-width="1.3"/>
  <line x1="422" y1="188" x2="410" y2="200" stroke="currentColor" stroke-width="1.3"/>
  <line x1="428" y1="194" x2="462" y2="194" stroke="currentColor" stroke-width="1.2" stroke-dasharray="4 3" opacity="0.5"/>
  <text x="416" y="240" fill="currentColor" text-anchor="middle" opacity="0.85">blackhole</text>
</svg>

Reconciling the doc with what I saw, the failover signal looks to be the endpoint ENI, not the path from it to the NLB. A backend that disappears behind a still-healthy ENI does not trip the probe.

So a zone drain has to be done on both accounts. If you take a zone out of the NLB, remove that zone from the endpoint too (delete the zone's endpoint ENI), or the endpoint keeps sending a share of traffic into the dead zone. The two are coupled by zone on the way up (the zone cascade) and on the way down just the same.

Related: [Alibaba PrivateLink zones cascade from the NLB](2026-09-07-alibaba-privatelink-zones-follow-nlb.md), the `endpoint zones ⊆ endpoint-service zones ⊆ NLB zones` rule.

Docs: [Create and manage endpoints](https://www.alibabacloud.com/help/en/privatelink/create-and-manage-endpoints/). PrivateLink probes each zone's endpoint ENI IP in real time and removes that zone's DNS record when it detects an anomaly, restoring it on recovery.
