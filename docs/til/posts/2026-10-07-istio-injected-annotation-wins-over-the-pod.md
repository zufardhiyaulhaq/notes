---
date: 2026-10-07
authors:
  - zufar
categories:
  - Kubernetes
tags:
  - kubernetes
  - istio
  - service-mesh
  - home-lab
---

# A mesh-wide injected annotation overrides the pod's own

Istio's usual rule is that a pod annotation overrides the mesh default. The sidecar injector's `injectedAnnotations` is the exception: when the mesh config and a pod set the same annotation, the mesh-wide value wins.

<!-- more -->

Say the mesh injects `sidecar.istio.io/statsEvictionInterval: "120s"` ([how to set that](2026-10-07-istio-inject-annotation-to-all-sidecars.md)) and a deployment sets its own:

```yaml
# deployment pod template
template:
  metadata:
    annotations:
      sidecar.istio.io/statsEvictionInterval: "30s"   # loses
```

The injected pod comes out with `120s`, not `30s`.

This is deliberate. `injectedAnnotations` were added so the mesh operator can force annotations (originally for PodSecurityPolicy), applied as a strategic merge patch at injection, so the injected value takes the key. That makes a mesh-wide annotation both the default and a ceiling: one place to set it, and no team can quietly opt out by annotating their own pod.

Useful when the value is something you want bounded everywhere (a metric eviction interval, a resource hint). Surprising if you expected per-pod annotations to win, like they usually do.

Docs: [installing the sidecar](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/), and the `injectedAnnotations` field in the inject package ([`istio.io/istio/pkg/kube/inject`](https://pkg.go.dev/istio.io/istio/pkg/kube/inject)).
