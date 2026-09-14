# WAL Archival

when implementing WAL Archival, there is only 1 data source that we can use which is object storage. this is implemented via barman cloud plugin https://cloudnative-pg.io/plugin-barman-cloud/docs/installation/.

1. Install Barman Cloud Plugin
2. Install minio (if required) & create bucket by accessing the minio portal
```
kubectl apply -f minio.yaml

kubectl port-forward svc/minio 9001:9001
http://127.0.0.1:9001/

k exec -it minio-77f9768885-9hljn -- bash
mc alias set myminio http://127.0.0.1:9000/ minioadmin minioadmin
mc mb myminio/wal-archival

mc admin accesskey create localminio/ --access-key miniouser --secret-key miniouser
```
3. Create object store & required secret
```
kubectl apply -f secret-example.yaml
kubectl apply -f object-store-example.yaml
```
1. apply the cluster with updated plugin
```
kubectl apply -f cluster.yaml

spec:
  plugins:
  - name: barman-cloud.cloudnative-pg.io
    isWALArchiver: true
    parameters:
      barmanObjectName: s3-object-store-wal-archival
```
4. Cluster will start the process of installing the plugin with sidecar, required master and replica restart
```
NAME                                   AGE    INSTANCES   READY   STATUS                                       PRIMARY
echo-postgresql                        10d    3           2       Waiting for the instances to become active   echo-postgresql-14

$ kubectl get pod
echo-postgresql-13                              1/1     Running   0          87m
echo-postgresql-14                              1/1     Running   0          88m
echo-postgresql-15                              1/2     Running   0          111s
```
5. We will see the primary postgresql logs (container plugin-barman-cloud) will start sending WAL archive to S3/Minio, while replica is not doing any WAL archival
```
k logs echo-postgresql-15 -c plugin-barman-cloud -f --tail 10

{"level":"info","ts":"2025-07-13T05:10:42.805540985Z","msg":"Applying backup retention policy","logging_pod":"echo-postgresql-15","retentionPolicy":"7d"}
{"level":"info","ts":"2025-07-13T05:11:08.709343548Z","msg":"Executing barman-cloud-wal-archive","logging_pod":"echo-postgresql-15","walName":"/var/lib/postgresql/data/pgdata/pg_wal/000000060000000000000073","options":["--gzip","--endpoint-url","http://minio:9000/","--cloud-provider","aws-s3","s3://wal-archival/","echo-postgresql","/var/lib/postgresql/data/pgdata/pg_wal/000000060000000000000073"]}
{"level":"info","ts":"2025-07-13T05:11:10.263064945Z","msg":"Archived WAL file","logging_pod":"echo-postgresql-15","walName":"/var/lib/postgresql/data/pgdata/pg_wal/000000060000000000000073","startTime":"2025-07-13T05:11:08.709335058Z","endTime":"2025-07-13T05:11:10.263039494Z","elapsedWalTime":1.553704436}

k logs echo-postgresql-14 -c plugin-barman-cloud -f --tail 10

{"level":"info","ts":"2025-07-13T05:15:44.062401857Z","msg":"Skipping retention policy enforcement, not the current primary","logging_pod":"echo-postgresql-14","currentPrimary":"echo-postgresql-15","podName":"echo-postgresql-14"}
```

## Manifests

??? example "cluster.yaml"

    ```yaml
    apiVersion: postgresql.cnpg.io/v1
    kind: Cluster
    metadata:
      name: echo-postgresql
      namespace: cnpg-system
    spec:
      instances: 3
      storage:
        size: 20Gi
        storageClass: gtf-ack-essd-pl0-wait
      walStorage:
        size: 1Gi
        storageClass: gtf-ack-essd-pl0-wait
      primaryUpdateStrategy: unsupervised
      primaryUpdateMethod: switchover
      postgresql:
        synchronous:
          method: any
          number: 1
          dataDurability: required
      backup:
        target: prefer-standby
        volumeSnapshot:
          className: alibabacloud-disk-snapshot
          online: false
      plugins:
      - name: barman-cloud.cloudnative-pg.io
        isWALArchiver: true
        parameters:
          barmanObjectName: s3-object-store-wal-archival
      resources:
        requests:
          cpu: 100m
          memory: 512Mi
        limits:
          cpu: 500m
          memory: 1Gi


    ```

??? example "minio-example.yaml"

    ```yaml
    ---
    apiVersion: v1
    kind: Service
    metadata:
      name: minio
    spec:
      type: ClusterIP
      ports:
        - name: http
          port: 9000
          targetPort: 9000
        - name: console
          port: 9001
          targetPort: 9001
      selector:
        app: minio
    ---
    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: minio-pvc
      labels:
        app: minio-pvc
    spec:
      accessModes:
        - ReadWriteOnce
      storageClassName: gtf-ack-essd-pl0-wait
      resources:
        requests:
          storage: 10Gi
    ---
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: minio
      labels:
        app: minio
    spec:
      selector:
        matchLabels:
          app: minio
      strategy:
        type: Recreate
      template:
        metadata:
          labels:
            app: minio
        spec:
          containers:
          - name: minio
            image: minio/minio:latest
            args:
            - server
            - /data
            - --console-address
            - ":9001"
            env:
            - name: MINIO_ROOT_USER
              value: "minioadmin"
            - name: MINIO_ROOT_PASSWORD
              value: "minioadmin"
            ports:
            - containerPort: 9000
            - containerPort: 9001
            volumeMounts:
            - name: storage
              mountPath: "/data"
          volumes:
          - name: storage
            persistentVolumeClaim:
              claimName: minio-pvc
    ```

??? example "object-store-example.yaml"

    ```yaml
    apiVersion: barmancloud.cnpg.io/v1
    kind: ObjectStore
    metadata:
      name: s3-object-store-wal-archival
      namespace: cnpg-system
    spec:
      configuration:
        destinationPath: "s3://wal-archival/"
        endpointURL: "http://minio:9000/"
        s3Credentials:
          accessKeyId:
            name: minio-wal-archival-creds
            key: ACCESS_KEY_ID
          secretAccessKey:
            name: minio-wal-archival-creds
            key: ACCESS_SECRET_KEY
        wal:
          compression: gzip
      retentionPolicy: "30d"
    ```

??? example "secret-example.yaml"

    ```yaml
    apiVersion: v1
    kind: Secret
    metadata:
      name: minio-wal-archival-creds
      namespace: cnpg-system
    data:
      ACCESS_KEY_ID: base64-encoded-access-key-id
      ACCESS_SECRET_KEY: base64-encoded-secret-key
    ```

https://cloudnative-pg.io/documentation/1.26/wal_archiving/
