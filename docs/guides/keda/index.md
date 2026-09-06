# KEDA Learning

1. to prevent flapping of replica, HPA by default set stabilization window of 300s if metrics is keep fluctuating. https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/#stabilization-window
2. to rewrite this behavior, you can configure `advanced` ScaledObject
```
spec:
  scaleTargetRef: {}
  minReplicaCount: 1
  maxReplicaCount: 20
  triggers: []
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 100
            periodSeconds: 15
```
