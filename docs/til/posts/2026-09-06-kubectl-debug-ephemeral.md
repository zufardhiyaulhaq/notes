---
date: 2026-09-06
authors:
  - zufar
categories:
  - Kubernetes
tags:
  - kubectl
  - debugging
---

# kubectl debug attaches an ephemeral container

When a pod has no shell (distroless or `scratch`), you can still get inside it
with an ephemeral container instead of rebuilding the image:

```bash
kubectl debug -it <pod> --image=busybox:1.36 --target=<container>
```

<!-- more -->

`--target` shares the process namespace of that container, so you can see its
processes and read its `/proc`. The ephemeral container disappears when you exit
— it never restarts and is not part of the pod spec.

Available since Kubernetes 1.23 (GA in 1.25).
