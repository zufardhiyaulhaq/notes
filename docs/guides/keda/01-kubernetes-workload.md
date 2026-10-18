# Kubernetes Workload
https://keda.sh/docs/2.18/scalers/kubernetes-workload/

We have target-deployment where it will autoscaled based on replica on reference-deployment. the scaledObject is referencing reference-deployment and scale the target deployment.

1. Create everything
```
kubectl apply -f .
deployment.apps/reference-nginx-deployment created
scaledobject.keda.sh/nginx-kubernetes-workload-scaler created
deployment.apps/target-nginx-deployment created

➜  keda-example git:(main) ✗ k get pod
NAME                                          READY   STATUS    RESTARTS   AGE
reference-nginx-deployment-59c749987f-7tf5z   1/1     Running   0          64s
target-nginx-deployment-584d8467dc-7cqsk      1/1     Running   0          64s

➜  keda-example git:(main) ✗ k get hpa
NAME                                        REFERENCE                            TARGETS     MINPODS   MAXPODS   REPLICAS   AGE
keda-hpa-nginx-kubernetes-workload-scaler   Deployment/target-nginx-deployment   1/1 (avg)   1         10        1          3m23s
```

2. Try to scale reference-deployment to 5 replica
```
➜  keda-example git:(main) ✗ k scale --replicas=5 deployment/reference-nginx-deployment
deployment.apps/reference-nginx-deployment scaled
(⎈|main-ps-sy-id-s-01:keda-testing) [29/12/25 | 7:03:21]
➜  keda-example git:(main) ✗ k get pod                                                 
NAME                                          READY   STATUS              RESTARTS   AGE
reference-nginx-deployment-59c749987f-7tf5z   1/1     Running             0          4m8s
reference-nginx-deployment-59c749987f-hfjkq   0/1     ContainerCreating   0          4s
reference-nginx-deployment-59c749987f-jqksb   0/1     ContainerCreating   0          4s
reference-nginx-deployment-59c749987f-zccjh   0/1     ContainerCreating   0          4s
reference-nginx-deployment-59c749987f-zd6zb   0/1     ContainerCreating   0          4s
```

3. KEDA automatically scale the target-deployment
```
➜  keda-example git:(main) ✗ k get hpa
NAME                                        REFERENCE                            TARGETS     MINPODS   MAXPODS   REPLICAS   AGE
keda-hpa-nginx-kubernetes-workload-scaler   Deployment/target-nginx-deployment   1/1 (avg)   1         10        5          4m41s
(⎈|main-ps-sy-id-s-01:keda-testing) [29/12/25 | 7:04:08]
➜  keda-example git:(main) ✗ k get pod
NAME                                          READY   STATUS    RESTARTS   AGE
reference-nginx-deployment-59c749987f-7tf5z   1/1     Running   0          5m6s
reference-nginx-deployment-59c749987f-hfjkq   1/1     Running   0          62s
reference-nginx-deployment-59c749987f-jqksb   1/1     Running   0          62s
reference-nginx-deployment-59c749987f-zccjh   1/1     Running   0          62s
reference-nginx-deployment-59c749987f-zd6zb   1/1     Running   0          62s
target-nginx-deployment-584d8467dc-4gmmh      1/1     Running   0          45s
target-nginx-deployment-584d8467dc-7cqsk      1/1     Running   0          5m6s
target-nginx-deployment-584d8467dc-9v9l6      1/1     Running   0          60s
target-nginx-deployment-584d8467dc-qp57r      1/1     Running   0          60s
target-nginx-deployment-584d8467dc-z5mgv      1/1     Running   0          60s
```

it will keep the same replica since we set value as '1'.
```
  triggers:
  - type: kubernetes-workload
    metadata:
      podSelector: 'app=reference-nginx'
      value: '1'
```

If we want to set the replica 2x of the reference-deployemnt, we can set the value as 0.5
```
  triggers:
  - type: kubernetes-workload
    metadata:
      podSelector: 'app=reference-nginx'
      value: '0.5'
```

If we want to set the replica only half of the reference-deployemnt, we can set the value as 2
```
  triggers:
  - type: kubernetes-workload
    metadata:
      podSelector: 'app=reference-nginx'
      value: '2'
```