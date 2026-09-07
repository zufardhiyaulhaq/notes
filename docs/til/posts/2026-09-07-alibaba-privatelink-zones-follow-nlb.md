---
date: 2026-09-07
authors:
  - zufar
categories:
  - Networking
tags:
  - alibaba-cloud
  - privatelink
  - networking
---

# Alibaba PrivateLink zones cascade from the NLB

On Alibaba Cloud PrivateLink you do not choose an endpoint's zones freely. Zones flow one way, from the load balancer outward, and each layer can only use the zones the layer beneath it already has.

<!-- more -->

The chain:

1. **Endpoint-service zones follow the NLB.** An endpoint service is built on a Network Load Balancer, so it can only offer a zone if the NLB is provisioned in that zone. You cannot add zone A to the service unless the NLB runs in zone A.
2. **Endpoint zones must be a subset of the endpoint-service zones.** A consumer endpoint can only cover zones the service already offers. So an endpoint cannot span three zones (A, B, C) when the service only covers two (B, C).

Net: `endpoint zones ⊆ endpoint-service zones ⊆ NLB zones`. To serve a zone end to end, add the NLB there first, then the endpoint service, then the endpoint. The three are effectively coupled by zone.

Related: an endpoint connects to the service in the same zone, and Zone Affinity makes the endpoint prefer the ENI in the client's own zone, so traffic stays in-zone when it can.

Docs: [Create and manage endpoints](https://www.alibabacloud.com/help/en/privatelink/create-and-manage-endpoints/), [Access NLB across VPCs via PrivateLink](https://www.alibabacloud.com/help/en/slb/network-load-balancer/use-cases/cross-vpc-private-network-access-through-privatelink).
