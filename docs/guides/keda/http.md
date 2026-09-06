# HTTP Scaler

this HTTP scaler can scale from 0 if there is any traffic, but the first X seconds of traffic will be delayed because cold start (similar like KNative serving). It's using experimental KEDA HTTP addon https://kedacore.github.io/http-add-on/ with additional CRDs called HTTPScaledObject

1. Create the deployment & service
```
kubectl apply -f nginx.yaml

➜  http git:(main) ✗ k get pod 
NAME                              READY   STATUS    RESTARTS   AGE
nginx-deployment-96b9d695-2d4c8   1/1     Running   0          40s
(⎈|main-ps-sy-id-s-01:keda-testing) [30/12/25 | 8:59:39]
➜  http git:(main) ✗ k get service
NAME            TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
nginx-service   ClusterIP   172.16.10.126   <none>        8080/TCP   7s
(⎈|main-ps-sy-id-s-01:keda-testing) [30/12/25 | 8:59:42]
➜  http git:(main) ✗ k get endpointslice
NAME                  ADDRESSTYPE   PORTS   ENDPOINTS        AGE
nginx-service-slvm2   IPv4          80      192.168.154.87   23s
```

to only scale the services when there is traffic, we will create HTTPScaledObject that is referencing the nginx deployment
```
  scaleTargetRef:
    name: nginx-deployment
    kind: Deployment
    apiVersion: apps/v1
```

and forward the traffic to the Kubernetes service
```
  scaleTargetRef:
    service: nginx-service
    port: 8080
```

it will create the HPA and scale down the deployment to 0
```
(⎈|main-ps-sy-id-s-01:keda-testing) [31/12/25 | 9:48:48]
➜  keda-example git:(main) ✗ k get pod
No resources found in keda-testing namespace.
(⎈|main-ps-sy-id-s-01:keda-testing) [31/12/25 | 9:49:39]
➜  keda-example git:(main) ✗ k get hpa
NAME                         REFERENCE                     TARGETS               MINPODS   MAXPODS   REPLICAS   AGE
keda-hpa-nginx-http-scaler   Deployment/nginx-deployment   <unknown>/100 (avg)   1         10        0          66s
(⎈|main-ps-sy-id-s-01:keda-testing) [31/12/25 | 9:49:40]
```

2. Calling the service

to call the service, we cannot call the kubernetes service directly, which is via nginx-service.keda-testing.svc.cluster.local. KEDA HTTP addon deploy an interceptor (located in namespace where you deploy the addon). We must call the interceptor and interceptor will provide metrics required by KEDA & HPA to scale the traffic.

```
(⎈|main-ps-sy-id-s-01:keda-testing) [31/12/25 | 9:53:55]
➜  keda-example git:(main) ✗ k get svc -n infrastructure | grep interceptor
keda-add-ons-http-interceptor-admin                    ClusterIP   172.16.13.136   <none>        9090/TCP           14h
keda-add-ons-http-interceptor-proxy                    ClusterIP   172.16.9.157    <none>        8080/TCP           14h
```

since the Interceptor act as reverse proxy & caching for the first request, in HTTPScaledObject, we must configure selector so the interceptor are able to forward the traffic properly.

```
spec:
  hosts:
  - "nginx.example.com"
  pathPrefixes:
  - /
```

so we must call the interceptor with Host header nginx.example.com. If translated to curl, this should looks like this
```
curl http://keda-add-ons-http-interceptor-proxy.infrastructure.svc.cluster.local:8080/ -H "Host: nginx.example.com"
```

In Istio virtual service, this should looks like this
```
  http:
  - match:
    - uri:
        prefix: /
    rewrite:
      authority: nginx.example.com
    route:
    - destination:
        host: keda-add-ons-http-interceptor-proxy.infrastructure.svc.cluster.local
        port: 8080
```

deploy some test pod
```
➜  keda-example git:(main) ✗ kubectl run client --image=nginx    
pod/client created
```

and try to call the service
```
(⎈|main-ps-sy-id-s-01:keda-testing) [31/12/25 | 9:58:50]
➜  keda-example git:(main) ✗ k exec -it client -- bash
root@client:/# curl http://keda-add-ons-http-interceptor-proxy.infrastructure.svc.cluster.local:8080/ -H "Host: nginx.example.com"
error on backend (context marked done while waiting for workload reach > 0 replicas: context deadline exceeded)root@client:/# 
root@client:/# curl http://keda-add-ons-http-interceptor-proxy.infrastructure.svc.cluster.local:8080/ -H "Host: nginx.example.com"
<!DOCTYPE html>
<html>
<head>
<title>Welcome to nginx!</title>
<style>
html { color-scheme: light dark; }
body { width: 35em; margin: 0 auto;
font-family: Tahoma, Verdana, Arial, sans-serif; }
</style>
</head>
<body>
<h1>Welcome to nginx!</h1>
<p>If you see this page, the nginx web server is successfully installed and
working. Further configuration is required.</p>

<p>For online documentation and support please refer to
<a href="http://nginx.org/">nginx.org</a>.<br/>
Commercial support is available at
<a href="http://nginx.com/">nginx.com</a>.</p>

<p><em>Thank you for using nginx.</em></p>
</body>
</html>
root@client:/# 
```

it's get timeout because of cold start issue. but the 2nd request is working and Pod is now scaled to 1
```
(⎈|main-ps-sy-id-s-01:keda-testing) [31/12/25 | 10:00:49]
➜  keda-example git:(main) ✗ k get pod
NAME                              READY   STATUS    RESTARTS   AGE
client                            1/1     Running   0          2m16s
nginx-deployment-96b9d695-gnx5c   1/1     Running   0          96s
```