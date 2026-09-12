---
date: 2026-09-12
authors:
  - zufar
categories:
  - Kubernetes
tags:
  - kubernetes
  - k3s
  - home-lab
---

# k3s leaves the control plane schedulable, so taint it

k3s does not taint its server nodes. Unlike a kubeadm cluster, a k3s control-plane node has no `node-role.kubernetes.io/control-plane:NoSchedule`, so it is schedulable and ordinary workloads land on it. On my Pi cluster I found regular pods sharing the control-plane node with the k3s server.

<!-- more -->

k3s runs workloads on the server by design, which is right for a single-node box and not what I want for a node that also holds the control plane. Two steps to dedicate it, plus one that is easy to miss.

Taint the node so new regular pods stay off:

```bash
kubectl --context kubernetes-cluster taint nodes k8s-master \
  node-role.kubernetes.io/control-plane=:NoSchedule --overwrite
```

Drain the pods that already scheduled there before the taint existed:

```bash
kubectl --context kubernetes-cluster drain k8s-master \
  --ignore-daemonsets --delete-emptydir-data --force --grace-period=30
```

Then uncordon it. `drain` also cordons the node (`SchedulingDisabled`), and a cordon blocks everything, including pods that tolerate the control-plane taint. Uncordon hands the gate back to the taint, so tolerating pods can still run while ordinary ones cannot:

```bash
kubectl --context kubernetes-cluster uncordon k8s-master
```

To make it stick on a fresh node, set the taint at install with `--node-taint` (or `node-taint` in `config.yaml`). That only applies when the node first registers, so for a node already running, the `kubectl taint` above is the way to do it.

Docs: [k3s advanced options](https://docs.k3s.io/advanced). k3s server nodes are schedulable by default; add a node taint to keep workloads off a dedicated control plane.
