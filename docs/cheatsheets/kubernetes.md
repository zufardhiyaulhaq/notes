---
tags:
  - kubernetes
  - kubectl
---

# Kubernetes

## Contexts & namespaces

```bash
kubectl config get-contexts
kubectl config use-context <ctx>
kubectl config set-context --current --namespace=<ns>
```

## Pods

```bash
kubectl get pods -A -o wide
kubectl get pod <pod> -o yaml
kubectl describe pod <pod>
```

## Debugging

```bash
# logs from the previous (crashed) container
kubectl logs <pod> -c <container> --previous

# shell into a distroless pod via an ephemeral container
kubectl debug -it <pod> --image=busybox:1.36 --target=<container>

# copy a file out of a pod
kubectl cp <ns>/<pod>:/path/to/file ./file
```

## Networking

```bash
kubectl get svc,ep -n <ns>
kubectl port-forward svc/<svc> 8080:80
```

## Rollouts

```bash
kubectl rollout status deploy/<name>
kubectl rollout undo deploy/<name>
kubectl rollout restart deploy/<name>
```
