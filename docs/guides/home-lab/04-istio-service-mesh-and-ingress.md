---
tags:
  - istio
  - service-mesh
  - kubernetes
  - home-lab
  - networking
---

# Service mesh and ingress with Istio

Istio does two jobs in the cluster: the service mesh (mTLS and sidecars between workloads) and the platform ingress that fronts every public app. Both are installed and upgraded GitOps-style from the same repo as everything else ([GitOps with ArgoCD](03-gitops-with-argocd.md)), and the public traffic reaches the gateway over an frp tunnel ([exposing web services](05-exposing-web-services-with-frp.md)).

Two constraints shaped it. The cluster is a five-node Pi lab, so every component is right-sized down from the reference manifests. And **Istio is moving its images onto Docker Hub, whose 200-pull / 6h anonymous limit per IP is untenable behind a single home NAT.**

## Install as a revision

1. **Version and revision are single-sourced.** A config file holds `istio.version: 1.30.4` and `istio.revision: 1-30-4` (the version dots become revision dashes). CI reads them and runs `istioctl install --revision 1-30-4`. Upgrading Istio is editing those two lines; CI redeploys.
2. **A `default` tag points workloads at the live revision.** After the control plane installs, CI runs `istioctl tag set default --revision 1-30-4 --overwrite`. Namespaces and workloads inject with `istio.io/rev: default`, so an upgrade needs no per-namespace edit: a new revision, then a re-point of the tag.

## Three gateways, all right-sized

Every gateway requests `32m` CPU and `32Mi` memory with hostname anti-affinity, so they spread across boards and stay in the Pi budget.

| Gateway | Role | Service type |
|---|---|---|
| public | internet ingress (PROXY protocol, TLS passthrough) | ClusterIP |
| egress | in-cluster egress only | ClusterIP |
| internal | in-cluster ingress only | ClusterIP |

Only the public gateway is reachable from outside, and only through the frp traffic relay.

## Mirror the images to GHCR

Docker Hub's anonymous limit would throttle a whole home NAT behind one IP, so `pilot` (istiod) and `proxyv2` (gateways, sidecars, istio-init) are mirrored to a GHCR repo. The `hub` is overridden in three places: the control-plane `IstioOperator` (`spec.hub`), every gateway `IstioOperator`, and the sidecar-injector ConfigMap (`values.global.hub`):

```yaml
# IstioOperator (control plane and each gateway)
spec:
  hub: ghcr.io/example/istio-mirror
  tag: 1.30.4
```

**Miss one spot and those pods pull from Docker Hub and hit the limit; miss the mirror for a new version and every pod `ImagePullBackOff`s** on a tag that does not exist yet.

## One object set per public host

Each public hostname gets the same bundle of objects in git, all synced by ArgoCD:

| Object | Purpose |
|---|---|
| Gateway | selects the public gateway, HTTP to HTTPS redirect, HTTPS at `minProtocolVersion: TLSV1_3` |
| VirtualService | routes the host to its backend Service |
| Certificate | cert-manager, a cluster issuer on Let's Encrypt DNS-01 |
| AuthorizationPolicy | the `ALLOW` rule for this host |
| ServiceEntry | registers the host as `MESH_INTERNAL` |
| DNSEndpoint | external-dns writes the public record |

**The public gateway is default-deny.** Because `ALLOW` `AuthorizationPolicy` objects exist on it, any host without its own `ALLOW` rule gets Istio `RBAC: access denied` (403). Adding a host means adding its authz; there is no implicit allow.

## Sidecar mode only

Two images are in play, `pilot` and `proxyv2`. No istio-cni, no ambient or ztunnel, by choice: neither earns its complexity on a five-node lab. For the sidecar-level knobs, raising header limits or stamping connection metadata onto requests, see the [HTTP header limits](../engineering-notes/http-header-limits.md) guide and the [Envoy header-operator](../../til/posts/2026-09-29-istio-custom-request-response-header-value-with-envoy-operators.md) and [injected-annotation](../../til/posts/2026-10-07-istio-inject-annotation-to-all-sidecars.md) notes.

## Trade-offs

- **The GHCR mirror is a manual step per upgrade.** Before bumping the version, re-mirror the new `pilot` and `proxyv2`, or CI pulls a tag that does not exist.
- **Default-deny punishes a forgotten object.** A host with a Gateway and VirtualService but no AuthorizationPolicy silently returns 403, so the failure looks like the app and not the mesh.
- **One more platform to keep current.** Istio runs a roughly quarterly release train and drops support N-2, so staying patched is recurring work.

## Sources

- Istio: [1.30 release notes](https://istio.io/latest/news/releases/1.30.x/), [revisions and tags](https://istio.io/latest/docs/setup/upgrade/canary/), [authorization](https://istio.io/latest/docs/reference/config/security/authorization-policy/).
