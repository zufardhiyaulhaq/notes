# Home Lab

Notes on the cluster the rest of these guides run on: a single-server k3s cluster on three Raspberry Pi 4B boards over WiFi, kept deliberately minimal. SQLite through kine for the datastore, local-path for storage, and the components k3s bundles swapped out for my own (Istio for ingress, a reverse tunnel such as frp to expose services). The interesting part is anchoring the cluster to a DNS name so a WiFi DHCP reshuffle never breaks it.

- [k3s on Raspberry Pi over WiFi](01-k3s-cluster-setup.md)
