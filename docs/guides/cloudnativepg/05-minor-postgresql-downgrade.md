# Minor Postgresql Downgrade

similar like minor postgresql downgrade, it's also respect the primaryUpdateStrategy & primaryUpdateStrategy.

1. downgrade the cluster
```
kubectl apply -f cluster.yaml

apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: echo-postgresql-upgrade-test
  namespace: cnpg-system
spec:
  imageName: ghcr.io/cloudnative-pg/postgresql:17.0
  instances: 2
  storage:
    size: 1Gi
  primaryUpdateStrategy: supervised
```
2. since this is supervised. replica will be automatically downgraded, and wait manual intervention to delete master pod or switchover
```
zufar.dhiyaullhaq@MacBookPro 5-minor-postgresql-downgrade % k get cluster
NAME                           AGE     INSTANCES   READY   STATUS                     PRIMARY
echo-postgresql-upgrade-test   4h53m   2           2       Waiting for user action    echo-postgresql-upgrade-test-1

echo-postgresql-upgrade-test-1             1/1     Running   0          12m
echo-postgresql-upgrade-test-2             1/1     Running   0          4m8s

zufar.dhiyaullhaq@MacBookPro 5-minor-postgresql-downgrade % k get pod echo-postgresql-upgrade-test-2 -oyaml | grep image
    image: ghcr.io/cloudnative-pg/postgresql:17.0

zufar.dhiyaullhaq@MacBookPro 5-minor-postgresql-downgrade % k get pod echo-postgresql-upgrade-test-1 -oyaml | grep image
    image: ghcr.io/cloudnative-pg/postgresql:17.5
```
3. switchover the master, there will be downtime for 5-10s
```
kubectl cnpg promote echo-postgresql-upgrade-test echo-postgresql-upgrade-test-2

zufar.dhiyaullhaq@MacBookPro 5-minor-postgresql-downgrade % k get cluster                                                                   
NAME                           AGE     INSTANCES   READY   STATUS                     PRIMARY
echo-postgresql                8d      5           5       Cluster in healthy state   echo-postgresql-8
echo-postgresql-upgrade-test   4h55m   2           1       Switchover in progress     echo-postgresql-upgrade-test-2

zufar.dhiyaullhaq@MacBookPro 5-minor-postgresql-downgrade % k get pod echo-postgresql-upgrade-test-2 -oyaml | grep image
    image: ghcr.io/cloudnative-pg/postgresql:17.0

zufar.dhiyaullhaq@MacBookPro 5-minor-postgresql-downgrade % k get pod echo-postgresql-upgrade-test-1 -oyaml | grep image
    image: ghcr.io/cloudnative-pg/postgresql:17.0
```

## Manifests

??? example "cluster.yaml"

    ```yaml
    apiVersion: postgresql.cnpg.io/v1
    kind: Cluster
    metadata:
      name: echo-postgresql-upgrade-test
      namespace: cnpg-system
    spec:
      imageName: ghcr.io/cloudnative-pg/postgresql:17.0
      instances: 2
      storage:
        size: 1Gi
        storageClass: gtf-ack-essd-pl0-wait
      ## supervised upgrade strategy ##
      primaryUpdateStrategy: supervised
      ## unsupervised upgrade strategy ##
      # primaryUpdateStrategy: unsupervised
      # primaryUpdateMethod: switchover
    ```

??? example "deployment.yaml"

    ```yaml
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: echo-postgresql-upgrade
      namespace: cnpg-system
      labels:
        app: echo-postgresql-upgrade
    spec:
      replicas: 1
      selector:
        matchLabels:
          app: echo-postgresql-upgrade
      template:
        metadata:
          labels:
            app: echo-postgresql-upgrade
        spec:
          containers:
          - name: echo-postgresql-upgrade
            image: ghcr.io/zufardhiyaulhaq/echo-postgresql:v1.0.0
            ports:
            - containerPort: 8080
              name: http
            env:
            - name: HTTP_PORT
              value: "8080"
            - name: POSTGRESQL_HOST
              value: "echo-postgresql-upgrade-test-rw.cnpg-system.svc.cluster.local"
            - name: POSTGRESQL_PORT
              value: "5432"
            - name: POSTGRESQL_DATABASE
              valueFrom:
                secretKeyRef:
                  name: echo-postgresql-upgrade-test-app
                  key: dbname
            - name: POSTGRESQL_USER
              valueFrom:
                secretKeyRef:
                  name: echo-postgresql-upgrade-test-app
                  key: user
            - name: POSTGRESQL_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: echo-postgresql-upgrade-test-app
                  key: password
            resources:
              requests:
                cpu: "100m"
                memory: "128Mi"
              limits:
                cpu: "500m"
                memory: "512Mi"
    ---
    apiVersion: v1
    kind: Service
    metadata:
      name: echo-postgresql-upgrade
      namespace: cnpg-system
    spec:
      selector:
        app: echo-postgresql-upgrade
      ports:
        - protocol: TCP
          port: 8080
          targetPort: http
      type: ClusterIP
    ```

