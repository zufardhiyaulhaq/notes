---
tags:
  - victoriametrics
  - grafana
  - observability
  - kubernetes
  - gitops
---

# Sync Grafana dashboards from Git with the sidecar and ConfigMaps

A dashboard you create or edit in the Grafana UI lives in Grafana's own database, on its PVC. Destroy the PVC or the Grafana pod and those dashboards are gone. The fix is to keep dashboards as code in Git and let the cluster re-provision them, so the running Grafana is disposable.

Self-hosted OSS Grafana has no built-in "pull dashboards from a Git URL" feature. Grafana 11 and 12 ship a newer Git Sync preview, and Grafana Cloud has provisioning-as-code, but you need neither. The GitOps-native answer that already ships with the chart is the **Grafana dashboard sidecar**.

This is written for the [victoria-metrics-k8s-stack](https://github.com/VictoriaMetrics/helm-charts/tree/master/charts/victoria-metrics-k8s-stack) chart, which bundles the upstream Grafana Helm chart, but it applies to any install of that Grafana chart.

## How the sidecar works

The Grafana Helm chart runs a sidecar container next to Grafana called `grafana-sc-dashboard`. It is the [`kiwigrid/k8s-sidecar`](https://github.com/kiwigrid/k8s-sidecar) image. Its default environment looks like this:

```
METHOD=WATCH
LABEL=grafana_dashboard
LABEL_VALUE=1
FOLDER=/var/lib/grafana/dashboards/default
RESOURCE=both
```

What it does:

1. Watches for ConfigMaps (and Secrets, because `RESOURCE=both`) in its namespace that carry the label `grafana_dashboard: "1"`.
2. Writes each object's data, the dashboard JSON, into the provisioning folder `/var/lib/grafana/dashboards/default`.
3. Calls Grafana's reload API, `POST /api/admin/provisioning/dashboards/reload`, so Grafana picks up the new file.

Because `METHOD=WATCH`, this is a live watch. Add or change a labeled ConfigMap and the sidecar writes the file and reloads within seconds.

!!! note "You do not restart Grafana to add a dashboard"
    This is the common misconception. The sidecar hot-reloads through the provisioning API. You never `kubectl rollout restart` Grafana to add or update a dashboard. A restart is only needed if you change the sidecar or Grafana config itself.

### Confirm your own setup

List the containers in the Grafana pod and you should see the sidecar:

```bash
kubectl -n <ns> get pod -l app.kubernetes.io/name=grafana \
  -o jsonpath='{range .items[0].spec.containers[*]}{.name}{"\n"}{end}'
```

```
grafana
grafana-sc-dashboard
grafana-sc-datasource
```

Read the sidecar env to see the label, folder, and method it watches:

```bash
kubectl -n <ns> get pod -l app.kubernetes.io/name=grafana \
  -o jsonpath='{.items[0].spec.containers[?(@.name=="grafana-sc-dashboard")].env}' | python3 -m json.tool
```

## Author dashboards as code

Store clean dashboard `.json` files in a repo and let Kustomize turn each one into a labeled ConfigMap, one ConfigMap per dashboard.

```
dashboards/
  node-overview.json
  ingress-overview.json
kustomization.yaml
```

```yaml
# kustomization.yaml
namespace: observability-system
generatorOptions:
  disableNameSuffixHash: true      # stable ConfigMap names, so re-applies overwrite
  labels:
    grafana_dashboard: "1"          # the label the sidecar watches
configMapGenerator:
  - name: grafana-dashboard-node-overview
    files:
      - dashboards/node-overview.json
  - name: grafana-dashboard-ingress-overview
    files:
      - dashboards/ingress-overview.json
```

Apply it:

```bash
kubectl apply -k .
```

`disableNameSuffixHash: true` matters. Without it, Kustomize appends a content hash to every ConfigMap name (`grafana-dashboard-node-overview-abc123`). With `kubectl apply` and no pruning, each edit creates a new hashed ConfigMap and leaves the old one behind, so you slowly collect orphaned ConfigMaps and duplicate dashboards. A stable name means a re-apply overwrites the same object in place.

## Make dashboards portable

When you export a dashboard from Grafana, pick the model that uses a **datasource template variable**, not one with a hardcoded datasource UID. The variable is `type: datasource`, `query: prometheus` (VictoriaMetrics speaks the Prometheus datasource API), and every panel references `${datasource}`:

```json
{
  "templating": {
    "list": [
      {
        "name": "datasource",
        "type": "datasource",
        "query": "prometheus"
      }
    ]
  }
}
```

Now the same JSON works in any cluster and the reader just picks the datasource from a dropdown at the top of the dashboard.

Watch for `__inputs` and `DS_` placeholders. An export sometimes wraps the datasource in an `__inputs` block with a `DS_PROMETHEUS` placeholder that expects substitution at import time. A clean model that uses a `datasource` template variable has none of that, so it provisions as-is with no extra find-and-replace step.

## The durability payoff

Once dashboards are ConfigMaps in Git:

- If the Grafana **PVC** is lost, the sidecar re-writes every dashboard from the ConfigMaps on startup and Grafana re-provisions them.
- If the Grafana **pod** is rescheduled or replaced, same thing.
- The ConfigMaps live in the cluster datastore, independent of the Grafana PVC, and they are reproducible from Git if the whole cluster is rebuilt.

Dashboards become disposable and reproducible. The source of truth is the JSON in Git, not a database on a volume.

## Gotchas

| Gotcha | What to do |
|---|---|
| **ConfigMap size limit** is about 1 MB (etcd / kine). A very large single dashboard can exceed it. | Gzip the JSON (the sidecar decompresses gzip content) or split the dashboard. |
| **Namespace scope.** By default the sidecar only watches its own namespace. | Set `searchNamespace: ALL` on the sidecar to watch every namespace. |
| **Folder placement.** Dashboards land in the "General" folder (no folder) by default. | Route a dashboard to a Grafana folder with the `grafana_dashboard_folder` annotation on the ConfigMap. |
| **Cannot find a dashboard by browsing.** | Open it by uid: `/d/<uid>`. A uid-based URL opens the dashboard regardless of which folder it is in. |
| **A provisioned dashboard is effectively read-only in the UI.** "Save" writes back to the provisioned model, not to a new copy. | To change it, edit the JSON in Git and commit. The Git JSON stays the source of truth. |

## Verify

1. The ConfigMap exists with the label:

    ```bash
    kubectl -n <ns> get cm -l grafana_dashboard=1
    ```

2. The sidecar imported it. Check its logs for the write and the reload:

    ```bash
    kubectl -n <ns> logs <grafana-pod> -c grafana-sc-dashboard
    ```

    ```
    Writing /var/lib/grafana/dashboards/default/node-overview.json
    Request to http://localhost:3000/api/admin/provisioning/dashboards/reload ... 200
    Dashboards config reloaded
    ```

3. Open the dashboard by uid in the browser: `/d/<uid>`.

## Sources

- Grafana Helm chart, [sidecar for dashboards](https://github.com/grafana/helm-charts/tree/main/charts/grafana#sidecar-for-dashboards) (the `sidecar.dashboards` values, `searchNamespace`, `folderAnnotation`).
- [`kiwigrid/k8s-sidecar`](https://github.com/kiwigrid/k8s-sidecar): `METHOD`, `LABEL`, `LABEL_VALUE`, `FOLDER`, `RESOURCE`, and reload behavior.
- Grafana docs: [provision dashboards](https://grafana.com/docs/grafana/latest/administration/provisioning/#dashboards) and the [admin provisioning reload API](https://grafana.com/docs/grafana/latest/developers/http_api/admin/#reload-provisioning-configurations).
- [victoria-metrics-k8s-stack](https://github.com/VictoriaMetrics/helm-charts/tree/master/charts/victoria-metrics-k8s-stack) chart, which bundles the Grafana chart.
