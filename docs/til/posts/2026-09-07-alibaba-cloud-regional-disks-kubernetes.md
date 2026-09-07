---
date: 2026-09-07
authors:
  - zufar
categories:
  - Kubernetes
tags:
  - alibaba-cloud
  - storage
  - kubernetes
---

# Alibaba Cloud has regional disks, and Kubernetes can use them

A regional ESSD disk on Alibaba Cloud replicates data synchronously across zones in the same region, so the volume survives a single zone going down. I only just learned you can back a Kubernetes PersistentVolume with one, which gives a stateful workload real cross-zone durability.

<!-- more -->

Two things are needed.

First, the CSI components must be **version 1.33.4 or later**, both `csi-plugin` and `csi-provisioner` (on a cluster running Kubernetes 1.26+).

Second, create a StorageClass with `parameters.type: cloud_regional_disk_auto`:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: alibabacloud-disk-regional
parameters:
  type: cloud_regional_disk_auto
provisioner: diskplugin.csi.alibabacloud.com
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
```

`WaitForFirstConsumer` is the important part. It delays disk creation until the pod is scheduled, so the disk is provisioned across the right zones. Without it the disk can be locked to the wrong zone and block the cross-zone failover, which defeats the whole point.

Docs: [Regional ESSD disks](https://www.alibabacloud.com/help/en/ecs/user-guide/regional-essd-disks), [Use regional ESSD disks on ACK](https://www.alibabacloud.com/help/en/ack/ack-managed-and-ack-dedicated/user-guide/use-regional-essd-disks).
