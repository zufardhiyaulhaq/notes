# ResourceQuota for the whole vcluster

**One ResourceQuota caps the entire virtual cluster.** vcluster renders `policies.resourceQuota` as a real ResourceQuota in the host namespace, so the sum of every pod across every virtual namespace is bounded by one object.

1. enable the quota and set the ceilings.
```yaml
policies:
  resourceQuota:
    enabled: true
    quota:
      requests.cpu: "4"
      requests.memory: 8Gi
      count/pods: "20"
```
2. enable a LimitRange too. A CPU or memory quota only admits a pod that declares requests; a pod with no requests is rejected by the quota. The LimitRange supplies default requests so those pods still count against the quota instead of being denied.
```yaml
policies:
  limitRange:
    enabled: true
    default:
      cpu: "1"
      memory: 512Mi
      ephemeral-storage: 8Gi
    defaultRequest:
      cpu: 100m
      memory: 128Mi
      ephemeral-storage: 3Gi
```
3. apply with Helm.
```
helm upgrade --install my-vcluster vcluster \
  --repo https://charts.loft.sh \
  --version 0.37.2 \
  -n my-vcluster --create-namespace \
  -f values.yaml
```
4. both objects land in the host namespace.
```
$ kubectl -n my-vcluster get resourcequota,limitrange
NAME                            REQUEST                                              LIMIT
resourcequota/vc-my-vcluster   requests.cpu: 0/4, requests.memory: 0/8Gi, ...

NAME                        CREATED AT
limitrange/vc-my-vcluster   2026-10-10T...
```
5. watch the ephemeral-storage default on small nodes. vcluster's default LimitRange requests **3Gi ephemeral-storage per container**. On a node with little disk, a handful of pods can exhaust it and go `Pending`. Lower `defaultRequest.ephemeral-storage` if that bites.
```yaml
policies:
  limitRange:
    defaultRequest:
      ephemeral-storage: 256Mi
```

Set `limitRange.enabled: auto` to turn the LimitRange on automatically whenever the ResourceQuota is on.

## Manifests

??? example "values.yaml"

    ```yaml
    policies:
      resourceQuota:
        enabled: true
        quota:
          requests.cpu: "4"
          requests.memory: 8Gi
          count/pods: "20"
      limitRange:
        enabled: true
        default:
          cpu: "1"
          memory: 512Mi
          ephemeral-storage: 8Gi
        defaultRequest:
          cpu: 100m
          memory: 128Mi
          ephemeral-storage: 3Gi
    ```

https://www.vcluster.com/docs/vcluster/configure/vcluster-yaml/policies/resource-quota
https://www.vcluster.com/docs/vcluster/configure/vcluster-yaml/policies/limit-range
