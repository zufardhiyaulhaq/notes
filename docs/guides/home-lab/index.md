# Home Lab

Notes on the cluster the rest of these guides run on: a five-node k3s cluster on Raspberry Pi over WiFi, one server and four workers, kept deliberately minimal. local-path for storage, the control-plane board tainted so workloads stay on the workers, and the components k3s bundles swapped out for my own (Istio for ingress, a reverse tunnel such as frp to expose services). The interesting part is anchoring the cluster to a DNS name so a WiFi DHCP reshuffle never breaks it.

- [k3s on Raspberry Pi over WiFi](01-k3s-cluster-setup.md)
