---
tags:
  - victoriametrics
  - observability
  - kubernetes
---

# VictoriaMetrics Learning

Notes from running the [victoria-metrics-k8s-stack](https://github.com/VictoriaMetrics/helm-charts/tree/master/charts/victoria-metrics-k8s-stack)
Helm chart in my home lab. The chart bundles VictoriaMetrics for storage, vmagent
for scraping, vmalert and Alertmanager for alerting, and Grafana for dashboards,
so most of what I learn is about how those pieces fit together on Kubernetes.

Everything here is open source and reproducible on any cluster. This is a series,
so it will grow as I add more of the stack.

## Guides

1. [Sync Grafana dashboards from Git with the sidecar and ConfigMaps](01-sync-grafana-dashboards-from-git.md): keep dashboards as code so a lost PVC does not lose your dashboards.
