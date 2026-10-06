---
tags:
  - k3s
  - kubernetes
  - home-lab
  - raspberry-pi
---

# k3s on Raspberry Pi over WiFi

My home-lab is a five-node k3s cluster on Raspberry Pi 4B boards: one server and four workers, about 34 GiB RAM and 20 cores between them. It runs my own workloads and is where I practice Kubernetes. The boards are on WiFi for now; wired ethernet is planned but not in place yet, so the whole design assumes the network can change under it.

| Node | Role | RAM | Node IP (wlan0) |
|---|---|---|---|
| rpi-1 | control-plane (tainted) | 3.7 GiB | 192.168.1.10 |
| rpi-2 | worker | 7.6 GiB | 192.168.1.11 |
| rpi-3 | worker | 7.6 GiB | 192.168.1.12 |
| rpi-4 | worker | 7.6 GiB | 192.168.1.13 |
| rpi-5 | worker | 7.6 GiB | 192.168.1.14 |

## Design decisions

- **Flannel pinned to `wlan0`.** The nodes are on WiFi, so the CNI stays on the WiFi interface and never touches the host routing table: `--flannel-iface=wlan0 --node-ip=<node-ip>`.
- **The API is a DNS name, not an IP.** `k8s.lab.example.com` resolves split-horizon: `/etc/hosts` on each node points it at the LAN IP, and a public record points it at a reverse tunnel so remote `kubectl` works over the tunnel on `6443`. Every identity the API server could answer to, including the IP it will have once wired to ethernet, is pre-loaded into the server certificate (the `--tls-san` flags in the install below), so an IP or interface change never re-issues certs. Workers join by the DNS name too, so the move to ethernet later is just an `/etc/hosts` edit plus a `--node-ip` / `--flannel-iface=eth0` change and a restart: no re-issued certificates, no worker rejoin.
- **Minimal components.** Keep CoreDNS, metrics-server, local-path (the default StorageClass), and network-policy. Disable Traefik, ServiceLB, and helm-controller, and bring my own (Istio for ingress).
- **local-path for storage.** A PVC is just a directory on whichever node the pod lands on. Zero-config, but not replicated (see trade-offs).
- **The control-plane board is tainted.** It is the 4 GB board, and when application pods landed on it they starved the API server (slow `kubectl`, lost leader leases). Taint it so workloads stay on the four 8 GB workers: `kubectl taint node rpi-1 node-role.kubernetes.io/control-plane=:NoSchedule`. k3s system pods (CoreDNS, local-path-provisioner, metrics-server) tolerate it and keep running there. It is a scheduling fence, not HA. See [k3s leaves the control plane schedulable](../../til/posts/2026-09-12-k3s-leaves-the-control-plane-schedulable.md) for the why and the drain/uncordon it needs.

## The install

Server, on the control-plane board:

```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION=v1.36.3+k3s1 sh -s - server \
  --node-ip=192.168.1.10 --flannel-iface=wlan0 \
  --tls-san=192.168.1.10 --tls-san=192.168.2.10 \
  --tls-san=rpi-1 --tls-san=k8s.lab.example.com \
  --disable=traefik --disable=servicelb --disable-helm-controller
```

Agents, one per worker (node-ip `.11` through `.14`):

```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION=v1.36.3+k3s1 \
  K3S_URL=https://k8s.lab.example.com:6443 K3S_TOKEN=<node-token> \
  sh -s - agent --node-ip=192.168.1.11 --flannel-iface=wlan0
```

Then taint the server (above). The node token is on the server at `/var/lib/rancher/k3s/server/node-token`.

## Trade-offs

- **No HA.** One control-plane node; if it is down, the API is down until it returns.
- **local-path is not replicated.** If a node dies, its PVC data is stranded and the pod cannot reschedule with it. More workers widen where a PVC can land, not whether it can move.
- **`/etc/hosts` must stay in sync** across every node, since the split-horizon name lives there, not in DNS.

## Sources

- k3s: [server install options](https://docs.k3s.io/cli/server).
