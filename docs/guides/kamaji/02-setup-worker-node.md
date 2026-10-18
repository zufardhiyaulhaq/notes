# Setup Worker Node

### Prepare the worker

Kamaji by default doesn't have worker provisioning flow. so you need to install the worker and it's depedencies manually (containerd, kubelet, kubeadm, etc) and join with Kamaji cluster via `kubeadm join`.

kubelet and kubeadm for worker node must be at the tenant's minor version (`v1.34` for `v1.34.12`). the worker node also must be able to reach the LoadBalancer IP on both ports:

```bash
nc -zv <lb-ip> 6443    # kube-apiserver
nc -zv <lb-ip> 8132    # konnectivity-server
```

### Join worker nodes

```bash
# generate a join command from the tenant control plane
kubeadm --kubeconfig test-control-plane.kubeconfig token create --print-join-command

# run the join command on the worker node
kubeadm join 192.168.1.201:6443 --token <redacted> --discovery-token-ca-cert-hash <redacted>

kubectl --kubeconfig test-control-plane.kubeconfig get nodes
NAME                               STATUS     ROLES    AGE     VERSION
ps-sy-id-s-kamaji-worker-test-01   NotReady   <none>   2m42s   v1.34.12

kubectl --kubeconfig test-control-plane.kubeconfig -n kube-system get pods
NAME                       READY   STATUS    RESTARTS   AGE
coredns-577f568d8b-cf2ng   0/1     Pending   0          32h
coredns-577f568d8b-cwlk4   0/1     Pending   0          32h
kube-proxy-pj8bc           1/1     Running   0          2m44s
```

(Worker prerequisites can be automated with Clastix's `yaki` script; for fully declarative nodes use the [Cluster API provider](https://github.com/clastix/cluster-api-control-plane-provider-kamaji).) ([kamaji-generic](https://kamaji.clastix.io/getting-started/kamaji-generic/))
