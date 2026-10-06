---
tags:
  - k3s
  - kubernetes
  - home-lab
  - raspberry-pi
---

# k3s on Raspberry Pi over WiFi

My home-lab is a single-server k3s cluster on three Raspberry Pi 4B boards: one server and two workers, aarch64, about 19 GiB RAM between them. It runs my own workloads and is where I practice Kubernetes.

Two hardware facts shaped every decision. The boards are **WiFi-only**, on DHCP leases that have already reshuffled once, so an IP change must not break the cluster. And the board I picked for the control plane is the weakest (4 GB against 8 GB on the workers), so the whole thing stays deliberately minimal.

| Node | Role | RAM | Node IP (wlan0) |
|---|---|---|---|
| rpi-1 | control-plane | 3.7 GiB | 192.168.1.10 |
| rpi-2 | worker | 7.6 GiB | 192.168.1.11 |
| rpi-3 | worker | 7.6 GiB | 192.168.1.12 |

## One server, SQLite through kine

It is a single-server cluster on **k3s v1.36.3+k3s1**, with the datastore being **SQLite through kine** (the default), on a USB SSD rather than the SD card. No embedded etcd, no external database.

That is a deliberate trade for simplicity, and kine keeps the door open: moving to Postgres or etcd later is a datastore swap, not a rebuild. The cost is no HA, which is fine on a home-lab (more on that at the end).

## Enable memory cgroups

k3s needs memory cgroups, and they are off by default on a Raspberry Pi. If yours are not enabled, add the kernel flags to the single line in `/boot/firmware/cmdline.txt` and reboot:

```text
cgroup_memory=1 cgroup_enable=memory
```

## Keep flannel on WiFi

Because the boards are WiFi-only, the CNI has to stay on `wlan0` and leave the OS routing table alone. flannel (the k3s default, VXLAN) is pinned to the interface, and each node advertises its WiFi IP:

```text
--flannel-iface=wlan0 --node-ip=<node-ip>
```

## Anchor the cluster to a DNS name, not an IP

This is the part that makes a WiFi, DHCP cluster survivable. The cluster's identity is a **DNS name**, `k8s.lab.example.com`, never a raw IP:

- It resolves split-horizon: `/etc/hosts` on every node points it at the LAN IP, and a public record points it at a reverse tunnel, so remote `kubectl` works over the tunnel on `6443` (something like frp handles that exposure).
- Every identity the API server could ever answer to is pre-loaded into its certificate, so an interface or IP change never forces a cert re-issue:

```text
--tls-san 192.168.1.10                    # wlan0, today
--tls-san 192.168.2.10                   # eth0, the day I wire it
--tls-san rpi-1
--tls-san k8s.lab.example.com
```

Workers join by the DNS name too, not the server IP. That is the whole point: the day I move these boards onto wired ethernet, the migration is an `/etc/hosts` edit plus `--node-ip` / `--flannel-iface=eth0` and a restart. No re-issued certificates, no worker rejoin.

## A minimal component set

Everything not needed for a bare cluster is disabled at install:

| Component | State | Reason |
|---|---|---|
| CoreDNS | kept | cluster DNS |
| metrics-server | kept | `kubectl top`, HPA |
| local-path | kept (default StorageClass) | node-local PVCs |
| network-policy | kept | k3s's own controller on flannel |
| Traefik | disabled | install ingress by hand (Istio) when needed |
| ServiceLB | disabled | no LoadBalancer services |
| helm-controller | disabled | run Helm manually |

`local-path` is the storage: a PVC becomes a directory on whichever node the pod lands on. Zero-config and good enough for a home-lab (the catch is in the trade-offs below).

## The install

Server, on the control-plane board:

```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION=v1.36.3+k3s1 sh -s - server \
  --node-ip=192.168.1.10 --flannel-iface=wlan0 \
  --tls-san=192.168.1.10 --tls-san=192.168.2.10 \
  --tls-san=rpi-1 --tls-san=k8s.lab.example.com \
  --disable=traefik --disable=servicelb --disable-helm-controller
```

Agents, on the two workers (node-ip `.11` / `.12`):

```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION=v1.36.3+k3s1 \
  K3S_URL=https://k8s.lab.example.com:6443 K3S_TOKEN=<node-token> \
  sh -s - agent --node-ip=192.168.1.11 --flannel-iface=wlan0
```

The node token is on the server at `/var/lib/rancher/k3s/server/node-token`. There are no taints: with only three small boards, workloads schedule on the server too. k3s leaves the server schedulable by default, and here I keep it that way; to dedicate it instead, see [k3s leaves the control plane schedulable](../../til/posts/2026-09-12-k3s-leaves-the-control-plane-schedulable.md).

## Trade-offs I accept

- **No HA.** SQLite means one control-plane node. If the server board is down, the API is down until it returns. A second server is not possible without first moving off SQLite to etcd or Postgres, which kine keeps cheap.
- **local-path is not replicated.** A PVC is a directory on one node; if that node dies, the data is stranded and the pod cannot reschedule with it.
- **`/etc/hosts` must stay in sync.** The split-horizon anchor lives in three hosts files, not in DNS.

## What runs on top

With the base cluster up, the rest is GitOps: ArgoCD syncs the workloads (Istio, cert-manager, and so on) from a Git repository. Running Postgres on the same cluster is a separate exercise, see the [CloudNativePG guide](../cloudnativepg/index.md).

## Sources

- k3s: [server install options](https://docs.k3s.io/cli/server) and [the kine datastore](https://docs.k3s.io/datastore).
