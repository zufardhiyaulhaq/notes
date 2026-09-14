# Major Upgrade with Logical Replication

This guide will help you walkthrough on how to do major PostgreSQL version upgrade between CNPG clusters.

References:

- https://cloudnative-pg.io/documentation/1.26/cloudnative-pg.v1/#postgresql-cnpg-io-v1-RoleConfiguration
- https://cloudnative-pg.io/documentation/1.26/declarative_role_management/
- https://cloudnative-pg.io/documentation/1.26/logical_replication/#example-of-live-migration-and-major-postgres-upgrade-with-logical-replication

### Preparing old version of Database
1. create cluster with version 16.9, we will also create different roles, user, and password for replication. the role name is logical_replication, where username and password use secret type basic auth.
```
---
apiVersion: v1
kind: Secret
metadata:
  name: echo-postgresql-16-9-logical-replication-creds
  namespace: cnpg-system
data:
  username: bG9naWNhbF9yZXBsaWNhdGlvbg==
  password: bG9naWNhbF9yZXBsaWNhdGlvbg==
type: kubernetes.io/basic-auth
---
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
spec:
  managed:
    roles:
      - name: logical_replication
        login: true
        replication: true
        passwordSecret:
          name: echo-postgresql-16-9-logical-replication-creds
        inRoles:
          - app
```
it will create new role that has permission to do replication and part of app role (can access app database). creating new role is necessary since role with replication have higher privilage compare to default role provided.

2. check the status and check the managed roles
```
k get cluster
NAME                   AGE   INSTANCES   READY   STATUS                     PRIMARY
echo-postgresql-16-9   20m   2           2       Cluster in healthy state   echo-postgresql-16-9-1

k describe cluster echo-postgresql-16-9
  Managed Roles Status:
    By Status:
      Not - Managed:
        app
      Reconciled:
        logical_replication
      Reserved:
        postgres
        streaming_replica
    Password Status:
      logical_replication:
        Transaction ID:  745
```
3. apply the publication to create the publisher
```
k apply -f cluster-16-9-publication.yaml
k get publication 
NAME                             AGE   CLUSTER                PG NAME                          APPLIED   MESSAGE
echo-postgresql-16-9-publisher   6s    echo-postgresql-16-9   echo-postgresql-16-9-publisher   true 
```
there are several field on the publication object
```
spec:
  cluster:
    name: echo-postgresql-16-9
  dbname: app
  name: echo-postgresql-16-9-publisher
  target:
    allTables: true
```
.spec.cluster.name refer to the CNPG cluster where the publisher will be created. it will be created on app database with the publisher name of echo-postgresql-16-9-publisher targeting all table.

4. check the publisher configuration, let's use the new user we created
```
kubectl port-forward svc/echo-postgresql-16-9-rw -n cnpg-system 5432:5432
psql -h 127.0.0.1 -p 5432 -d app -U logical_replication

 app=> SELECT pubname, puballtables, pubinsert, pubupdate, pubdelete, pubtruncate, pubviaroot                                                                        FROM pg_publication;
            pubname             | puballtables | pubinsert | pubupdate | pubdelete | pubtruncate | pubviaroot 
--------------------------------+--------------+-----------+-----------+-----------+-------------+------------
 echo-postgresql-16-9-publisher | t            | t         | t         | t         | t           | f

kubectl cnpg psql echo-postgresql-16-9
postgres=# SELECT rolname FROM pg_roles WHERE rolreplication = true;
       rolname       
---------------------
 postgres
 streaming_replica
 logical_replication
(3 rows)
```
5. create the deployment that connect to old database and test the query
```
k apply -f deployment-16-9.yaml

k port-forward svc/echo-postgresql-upgrade 8080:8080

curl http://localhost:8080/postgresql/test
94ac2f1b-eba3-4e39-9e96-11289b5d5fd7:test

kubectl cnpg psql echo-postgresql-16-9
postgres=# \c app
You are now connected to database "app" as user "postgres".
app=# SELECT * FROM echos;
          created_at           |          updated_at          | deleted_at |                  id                  | echo 
-------------------------------+------------------------------+------------+--------------------------------------+------
 2025-11-10 10:38:41.754726+00 | 2025-11-10 10:38:41.75229+00 |            | 94ac2f1b-eba3-4e39-9e96-11289b5d5fd7 | test
(1 row)
```
6. Check the schema on old database
```
kubectl cnpg psql echo-postgresql-16-9

postgres=# \c app
You are now connected to database "app" as user "postgres".
app=# \d+ echos
                                                     Table "public.echos"
   Column   |           Type           | Collation | Nullable | Default | Storage  | Compression | Stats target | Description 
------------+--------------------------+-----------+----------+---------+----------+-------------+--------------+-------------
 created_at | timestamp with time zone |           |          |         | plain    |             |              | 
 updated_at | timestamp with time zone |           |          |         | plain    |             |              | 
 deleted_at | timestamp with time zone |           |          |         | plain    |             |              | 
 id         | character varying(255)   |           | not null |         | extended |             |              | 
 echo       | character varying(255)   |           | not null |         | extended |             |              | 
Indexes:
    "echos_pkey" PRIMARY KEY, btree (id)
    "idx_echos_deleted_at" btree (deleted_at)
Publications:
    "echo-postgresql-16-9-publisher"
Access method: heap
```

### Creating new version of Database
similar when we migrate postgresql to CNPG. we also need to do the samething by importing the schema from older version of database. we will use spec.externalClusters and spec.bootstrap

1. create the new database, as usual it will create import job
```
k apply -f cluster18-0.yaml

k get pod | grep import
echo-postgresql-18-0-1-import-qjvfr             0/1     Completed   0              21s```
```

2. check the schema of the new database and validate if records still empty
```
kubectl cnpg psql echo-postgresql-18-0
psql (18.0 (Debian 18.0-1.pgdg11+3))
Type "help" for help.

postgres=# \c app
You are now connected to database "app" as user "postgres".
app=# \d+ echos
                                                     Table "public.echos"
   Column   |           Type           | Collation | Nullable | Default | Storage  | Compression | Stats target 
| Description 
------------+--------------------------+-----------+----------+---------+----------+-------------+--------------
+-------------
 created_at | timestamp with time zone |           |          |         | plain    |             |              
| 
 updated_at | timestamp with time zone |           |          |         | plain    |             |              
| 
 deleted_at | timestamp with time zone |           |          |         | plain    |             |              
| 
 id         | character varying(255)   |           | not null |         | extended |             |              
| 
 echo       | character varying(255)   |           | not null |         | extended |             |              
| 
Indexes:
    "echos_pkey" PRIMARY KEY, btree (id)
    "idx_echos_deleted_at" btree (deleted_at)
Publications:
    "echo-postgresql-16-9-publisher"
Not-null constraints:
    "echos_id_not_null" NOT NULL "id"
    "echos_echo_not_null" NOT NULL "echo"
Access method: heap

app=# select * from echos;
 created_at | updated_at | deleted_at | id | echo 
------------+------------+------------+----+------
(0 rows)
```

3. let's create the subscription object. this will help sync data from old version of CNPG to new version of CNPG.
```
k apply -f cluster-18-0-subscription.yaml

k get subscription echo-postgresql-18-0-subscription
NAME                                AGE   CLUSTER                PG NAME      APPLIED   MESSAGE
echo-postgresql-18-0-subscription   3s    echo-postgresql-18-0   subscriber   true

kubectl cnpg psql echo-postgresql-18-0
postgres=# \c app
You are now connected to database "app" as user "postgres".

app=# select * from echos;
          created_at           |          updated_at          | deleted_at |                  id                  | echo 
-------------------------------+------------------------------+------------+--------------------------------------+------
 2025-11-10 10:38:41.754726+00 | 2025-11-10 10:38:41.75229+00 |            | 94ac2f1b-eba3-4e39-9e96-11289b5d5fd7 | test
```

4. try to call the deployment
```
curl http://localhost:8080/postgresql/test          
b3bf1519-bac2-44c2-b27a-033edeb37419:test

validate on new postgresql
app=# select * from echos;
          created_at           |          updated_at           | deleted_at |                  id                  | echo 
-------------------------------+-------------------------------+------------+--------------------------------------+------
 2025-11-10 10:38:41.754726+00 | 2025-11-10 10:38:41.75229+00  |            | 94ac2f1b-eba3-4e39-9e96-11289b5d5fd7 | test
 2025-11-10 11:12:48.512402+00 | 2025-11-10 11:12:48.511884+00 |            | b3bf1519-bac2-44c2-b27a-033edeb37419 | test
(2 rows)
```

### Switchover the service to new database
1. stop the service
```
kubectl delete -f deployment-16-9.yaml
```

2. delete the subscription
```
kubectl delete -f cluster-18-0-subscription.yaml
```

3. change service and point to CNPG version 18
```
kubectl apply -f deployment-18-0.yaml 
```

4. test calling the new deployment 
```
k port-forward svc/echo-postgresql-upgrade 8080:8080

curl http://localhost:8080/postgresql/test
84c760b8-3ab9-46ad-bae7-f282a0ff77c4:test
```

5. validate if records only populated on new CNPG version
```
kubectl cnpg psql echo-postgresql-18-0

psql (18.0 (Debian 18.0-1.pgdg11+3))
Type "help" for help.

postgres=# \c app
You are now connected to database "app" as user "postgres".
app=# select * from echos;
          created_at           |          updated_at           | deleted_at |                  id                  | echo 
-------------------------------+-------------------------------+------------+--------------------------------------+------
 2025-11-10 10:38:41.754726+00 | 2025-11-10 10:38:41.75229+00  |            | 94ac2f1b-eba3-4e39-9e96-11289b5d5fd7 | test
 2025-11-10 11:12:48.512402+00 | 2025-11-10 11:12:48.511884+00 |            | b3bf1519-bac2-44c2-b27a-033edeb37419 | test
 2025-11-10 11:17:07.423937+00 | 2025-11-10 11:17:07.420152+00 |            | 84c760b8-3ab9-46ad-bae7-f282a0ff77c4 | test
(3 rows)

app=# 
```

6. validate old database
```
kubectl cnpg psql echo-postgresql-16-9

psql (16.9 (Debian 16.9-1.pgdg110+1))
Type "help" for help.

postgres=# \c app
You are now connected to database "app" as user "postgres".
app=# select * from echos;
          created_at           |          updated_at           | deleted_at |                  id                  | echo 
-------------------------------+-------------------------------+------------+--------------------------------------+------
 2025-11-10 10:38:41.754726+00 | 2025-11-10 10:38:41.75229+00  |            | 94ac2f1b-eba3-4e39-9e96-11289b5d5fd7 | test
 2025-11-10 11:12:48.512402+00 | 2025-11-10 11:12:48.511884+00 |            | b3bf1519-bac2-44c2-b27a-033edeb37419 | test
(2 rows)

app=# 
```

## Manifests

??? example "cluster-16-9-publication.yaml"

    ```yaml

    apiVersion: postgresql.cnpg.io/v1
    kind: Publication
    metadata:
      name: echo-postgresql-16-9-publisher
    spec:
      cluster:
        name: echo-postgresql-16-9
      dbname: app
      name: echo-postgresql-16-9-publisher
      target:
        allTables: true
    ```

??? example "cluster-18-0-subscription.yaml"

    ```yaml

    ---
    apiVersion: postgresql.cnpg.io/v1
    kind: Subscription
    metadata:
      name: echo-postgresql-18-0-subscription
    spec:
      cluster:
        name: echo-postgresql-18-0
      dbname: app
      name: subscriber
      externalClusterName: echo-postgresql-16-9
      publicationName: echo-postgresql-16-9-publisher
    ```

??? example "cluster16-9.yaml"

    ```yaml
    ---
    apiVersion: v1
    kind: Secret
    metadata:
      name: echo-postgresql-16-9-logical-replication-creds
      namespace: cnpg-system
      labels:
        cnpg.io/reload: "true"
    data:
      username: bG9naWNhbF9yZXBsaWNhdGlvbg==
      password: bG9naWNhbF9yZXBsaWNhdGlvbg==
    type: kubernetes.io/basic-auth
    ---
    apiVersion: postgresql.cnpg.io/v1
    kind: Cluster
    metadata:
      name: echo-postgresql-16-9
      namespace: cnpg-system
    spec:
      imageName: ghcr.io/cloudnative-pg/postgresql:16.9
      instances: 2
      storage:
        size: 1Gi
        storageClass: gtf-ack-essd-pl0-wait
      managed:
        roles:
          - name: logical_replication
            login: true
            replication: true
            ensure: present
            passwordSecret:
              name: echo-postgresql-16-9-logical-replication-creds
            inRoles:
              - app
      walStorage:
        size: 1Gi
        storageClass: gtf-ack-essd-pl0-wait
      primaryUpdateStrategy: unsupervised
      primaryUpdateMethod: switchover
      postgresql:
        parameters:
          archive_timeout: "10min"
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

??? example "cluster18-0.yaml"

    ```yaml

    apiVersion: postgresql.cnpg.io/v1
    kind: Cluster
    metadata:
      name: echo-postgresql-18-0
      namespace: cnpg-system
    spec:
      imageName: ghcr.io/cloudnative-pg/postgresql:18.0
      instances: 2
      externalClusters:
      - name: echo-postgresql-16-9
        connectionParameters:
          host: echo-postgresql-16-9-rw.cnpg-system.svc.cluster.local
          user: logical_replication
          dbname: app
        password:
          name: echo-postgresql-16-9-logical-replication-creds
          key: password
      bootstrap:
        initdb:
          import:
            type: microservice
            schemaOnly: true
            databases:
              - app
            source:
              externalCluster: echo-postgresql-16-9
      storage:
        size: 1Gi
        storageClass: gtf-ack-essd-pl0-wait
      walStorage:
        size: 1Gi
        storageClass: gtf-ack-essd-pl0-wait
      primaryUpdateStrategy: unsupervised
      primaryUpdateMethod: switchover
      postgresql:
        parameters:
          archive_timeout: "10min"
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

??? example "deployment-16-9.yaml"

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
            image: ghcr.io/zufardhiyaulhaq/echo-postgresql:v1.0.1
            ports:
            - containerPort: 8080
              name: http
            env:
            - name: HTTP_PORT
              value: "8080"
            - name: POSTGRESQL_HOST
              value: "echo-postgresql-16-9-rw.cnpg-system.svc.cluster.local"
            - name: POSTGRESQL_PORT
              value: "5432"
            - name: POSTGRESQL_DATABASE
              valueFrom:
                secretKeyRef:
                  name: echo-postgresql-16-9-app
                  key: dbname
            - name: POSTGRESQL_USER
              valueFrom:
                secretKeyRef:
                  name: echo-postgresql-16-9-app
                  key: user
            - name: POSTGRESQL_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: echo-postgresql-16-9-app
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

??? example "deployment-18-0.yaml"

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
            image: ghcr.io/zufardhiyaulhaq/echo-postgresql:v1.0.1
            ports:
            - containerPort: 8080
              name: http
            env:
            - name: HTTP_PORT
              value: "8080"
            - name: POSTGRESQL_HOST
              value: "echo-postgresql-18-0-rw.cnpg-system.svc.cluster.local"
            - name: POSTGRESQL_PORT
              value: "5432"
            - name: POSTGRESQL_DATABASE
              valueFrom:
                secretKeyRef:
                  name: echo-postgresql-18-0-app
                  key: dbname
            - name: POSTGRESQL_USER
              valueFrom:
                secretKeyRef:
                  name: echo-postgresql-18-0-app
                  key: user
            - name: POSTGRESQL_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: echo-postgresql-18-0-app
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

