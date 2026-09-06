---
tags:
  - kubernetes
  - kubeadm
  - certificates
---

# Renew a kubeadm Kubernetes cluster certificate

Check when the control-plane certificates expire:

```bash
kubeadm alpha certs check-expiration
```

Renew all of them:

```bash
kubeadm alpha certs renew all
```

!!! note
    This only renews certificates on the **control-plane (master)** node. kubeadm
    automatically renews kubelet/worker certificates before they expire.

!!! tip "Newer clusters"
    The `alpha` prefix was promoted in Kubernetes 1.20+. On current clusters use
    `kubeadm certs check-expiration` and `kubeadm certs renew all`.

## Example output

```text
root@k8s-community-master:~# kubeadm alpha certs check-expiration
[check-expiration] Reading configuration from the cluster...

CERTIFICATE                EXPIRES                  RESIDUAL TIME   CERTIFICATE AUTHORITY   EXTERNALLY MANAGED
admin.conf                 Feb 11, 2021 11:11 UTC   364d                                    no
apiserver                  Feb 11, 2021 11:11 UTC   364d            ca                      no
apiserver-etcd-client      Feb 11, 2021 11:11 UTC   364d            etcd-ca                 no
apiserver-kubelet-client   Feb 11, 2021 11:11 UTC   364d            ca                      no
controller-manager.conf    Feb 11, 2021 11:11 UTC   364d                                    no
etcd-healthcheck-client    Feb 11, 2021 11:11 UTC   364d            etcd-ca                 no
etcd-peer                  Feb 11, 2021 11:11 UTC   364d            etcd-ca                 no
etcd-server                Feb 11, 2021 11:12 UTC   364d            etcd-ca                 no
front-proxy-client         Feb 11, 2021 11:12 UTC   364d            front-proxy-ca          no
scheduler.conf             Feb 11, 2021 11:12 UTC   364d                                    no

root@k8s-community-master:~# kubeadm alpha certs renew all
certificate embedded in the kubeconfig file for the admin to use ... renewed
certificate for serving the Kubernetes API renewed
certificate the apiserver uses to access etcd renewed
certificate for the API server to connect to kubelet renewed
certificate embedded in the kubeconfig file for the controller manager ... renewed
certificate for liveness probes to healthcheck etcd renewed
certificate for etcd nodes to communicate with each other renewed
certificate for serving etcd renewed
certificate for the front proxy client renewed
certificate embedded in the kubeconfig file for the scheduler manager ... renewed
```

After renewing, restart the control-plane static pods (or the node) so they pick
up the new certificates.
