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

# Inject an annotation into every Istio sidecar

You do not have to edit every deployment to put a sidecar annotation on your workloads. Istio's injector can stamp a fixed annotation onto every pod it injects, from one place in the mesh config: `values.sidecarInjectorWebhook.injectedAnnotations`.

<!-- more -->

I wanted every sidecar in the mesh to carry `sidecar.istio.io/statsEvictionInterval` without touching hundreds of deployments:

```yaml
# IstioOperator
spec:
  values:
    sidecarInjectorWebhook:
      injectedAnnotations:
        sidecar.istio.io/statsEvictionInterval: "120s"
```

Every pod the sidecar injector touches comes out with that annotation, so the whole mesh picks it up on the next rollout. No per-deployment edits, no mutating hundreds of manifests.

Read it back off a running pod to confirm:

```bash
kubectl get pod <pod> -o jsonpath='{.metadata.annotations.sidecar\.istio\.io/statsEvictionInterval}'
```

One thing to know before you lean on it: a value set here also overrides a pod that sets the same annotation itself. That is its own note: [a mesh-wide injected annotation overrides the pod's own](2026-10-07-istio-injected-annotation-wins-over-the-pod.md).

Docs: [installing the sidecar](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/), and the `injectedAnnotations` field in the inject package ([`istio.io/istio/pkg/kube/inject`](https://pkg.go.dev/istio.io/istio/pkg/kube/inject)).
