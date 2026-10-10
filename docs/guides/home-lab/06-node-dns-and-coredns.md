---
tags:
  - coredns
  - dns
  - k3s
  - kubernetes
  - home-lab
---

# Pointing CoreDNS at a reachable upstream resolver

**One change took down every public ingress at once, and it looked like a control-plane fault until it traced back to DNS.** CoreDNS stopped resolving any external name, answering `SERVFAIL` and "server misbehaving". external-dns could not reach Cloudflare, ArgoCD could not fetch its charts, cert-manager could not reach Let's Encrypt, and the frp traffic client could not resolve its own relay. Everything that depends on an outbound name went down together.

The nodes themselves resolved fine. The break was one layer down, in the resolver CoreDNS had inherited.

## The cause

The home ISP and router block public DNS resolvers. Only the router's own resolver answers:

| Resolver | Result from a node |
|---|---|
| `8.8.8.8` / `8.8.4.4` | blocked (no answer) |
| `1.1.1.1` | blocked (connection refused) |
| `192.168.1.1` (router) | answers |

**CoreDNS was forwarding to `8.8.8.8`, the one resolver the ISP blocks.** The nodes were healthy because systemd-resolved gets the router from DHCP. The chain: the host `/etc/resolv.conf` is the systemd-resolved stub (`nameserver 127.0.0.53`), which k3s cannot hand into a pod, so k3s substitutes its hardcoded fallback `8.8.8.8 / 8.8.4.4`. CoreDNS's Corefile is `forward . /etc/resolv.conf`, and that file, inside the pod, pointed at the blocked fallback.

## The fix

Pin k3s to the real systemd-resolved uplink file, so CoreDNS forwards to the same resolver every node already uses. On the server:

```yaml
# /etc/rancher/k3s/config.yaml
resolv-conf: "/run/systemd/resolve/resolv.conf"
```

That file lists the real uplink (`nameserver 192.168.1.1`), not the stub. Apply it by restarting k3s so it re-templates the pod `resolv.conf`, then rolling CoreDNS so it re-reads the forward target:

```bash
sudo systemctl restart k3s
kubectl -n kube-system rollout restart deploy coredns
```

The Corefile does not change; it stays `forward . /etc/resolv.conf`. **You fix what that file resolves to, not the Corefile.** This is a k3s-level setting, not an edit to the CoreDNS ConfigMap, which k3s manages and would overwrite. Because the fix lives in k3s config, it survives a reboot and a k3s restart. Verify from a node:

```bash
dig +short google.com @10.43.0.10
```

## Trade-offs

- **A node rebuild must keep this file or the outage returns.** The GitOps deployer ([GitOps with ArgoCD](03-gitops-with-argocd.md)) rebuilds the cluster but not this host-level config. Any reinstall of the k3s server has to re-create `/etc/rancher/k3s/config.yaml` with the `resolv-conf` line, or CoreDNS falls back to the blocked resolver again.
- **CoreDNS is a single DNS point of failure.** The deployment runs 1 replica, it tolerates the control-plane taint, and it tends to land on the weakest board. When that pod or node is down, cluster DNS is down. The fix is to scale to 2 replicas with pod anti-affinity once a second board can carry it.

## Sources

- k3s: [`resolv-conf` server flag](https://docs.k3s.io/cli/server).
- CoreDNS: [the `forward` plugin](https://coredns.io/plugins/forward/).
