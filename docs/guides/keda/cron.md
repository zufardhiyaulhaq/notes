# Cron
https://keda.sh/docs/2.18/scalers/cron/

before 10:52 AM
```
nginx-deployment   0/0     0            0           15s
(⎈|main-ps-sy-id-s-01:keda-testing) [29/12/25 | 10:51:38]
➜  cron k get deploy
NAME               READY   UP-TO-DATE   AVAILABLE   AGE
nginx-deployment   0/0     0            0           18s
(⎈|main-ps-sy-id-s-01:keda-testing) [29/12/25 | 10:51:40]
➜  cron k get hpa   
NAME                         REFERENCE                     TARGETS             MINPODS   MAXPODS   REPLICAS   AGE
keda-hpa-nginx-cron-scaler   Deployment/nginx-deployment   <unknown>/1 (avg)   1         10        0          19s
```

in 10:52 AM
```
(⎈|main-ps-sy-id-s-01:keda-testing) [29/12/25 | 10:53:05]
➜  cron k get hpa
NAME                         REFERENCE                     TARGETS     MINPODS   MAXPODS   REPLICAS   AGE
keda-hpa-nginx-cron-scaler   Deployment/nginx-deployment   1/1 (avg)   1         10        5          107s
(⎈|main-ps-sy-id-s-01:keda-testing) [29/12/25 | 10:53:10]
➜  cron k get pod
NAME                              READY   STATUS              RESTARTS   AGE
nginx-deployment-96b9d695-2l6g6   0/1     ContainerCreating   0          45s
nginx-deployment-96b9d695-649gf   1/1     Running             0          30s
nginx-deployment-96b9d695-bzz9z   1/1     Running             0          61s
nginx-deployment-96b9d695-kjggx   0/1     ContainerCreating   0          45s
nginx-deployment-96b9d695-ttsr2   1/1     Running             0          45s
```

after 10:55 AM, and additional cooling down period of default 300s, https://keda.sh/docs/2.18/scalers/cron/.  scaling down will happen 5 minutes after the cron schedule end parameter.
```
(⎈|main-ps-sy-id-s-01:keda-testing) [29/12/25 | 11:00:02]
➜  cron k get hpa
NAME                         REFERENCE                     TARGETS             MINPODS   MAXPODS   REPLICAS   AGE
keda-hpa-nginx-cron-scaler   Deployment/nginx-deployment   <unknown>/1 (avg)   1         10        0          8m40s
(⎈|main-ps-sy-id-s-01:keda-testing) [29/12/25 | 11:00:03]
➜  cron k get pod
No resources found in keda-testing namespace.
```
