# Home Lab

A five-node k3s cluster on Raspberry Pi over WiFi, one server and four workers, ~34 GiB RAM and 20 cores between them. It runs my own workloads and is where I practice Kubernetes. local-path for storage, the control-plane board tainted so workloads stay on the four workers, the components k3s bundles swapped out for my own (Istio for ingress, frp reverse tunnels to reach it from outside). **The whole design assumes the network can change under it**, so the cluster is anchored to a DNS name that a WiFi DHCP reshuffle never breaks.

One page per decision, written generically so the pattern is reusable without my network's specifics:

- [Kubernetes installation with k3s](01-k3s-cluster-setup.md): the five boards, the minimal component set, the DNS-anchored API, and why the control-plane board is tainted.
- [Remote access with frp reverse tunnels](02-remote-access-with-frp.md): SSH to every board and `kubectl` against the API from anywhere, without opening the home router.
- [GitOps for the cluster with ArgoCD](03-gitops-with-argocd.md): helmfile, Kustomize, app-of-apps, and ArgoCD, deployed in a fixed order from one Git repo.
- [Service mesh and ingress with Istio](04-istio-service-mesh-and-ingress.md): a revisioned Istio install, GHCR-mirrored images, and a default-deny public gateway.
- [Exposing web services with frp-operator](05-exposing-web-services-with-frp.md): a dedicated traffic relay, PROXY protocol to keep the real client IP, and declarative DNS.
- [Pointing CoreDNS at a reachable upstream resolver](06-node-dns-and-coredns.md): the DNS fault that took down every public ingress at once, and the one-line k3s fix.
- [A backup access path with Tailscale](07-backup-access-with-tailscale.md): a break-glass path into the cluster for when frp is the thing that is down.
