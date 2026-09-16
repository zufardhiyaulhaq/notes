---
date: 2026-09-16
authors:
  - zufar
categories:
  - Containers
tags:
  - ghcr
  - containers
  - github
---

# GHCR rate-limits 40k/minutes

GitHub Container Registry throttles pulls per **namespace**, namespace is the organization or user that owns the image. Every pull of every image under one owner draws from a single bucket. Cross the limit and pulls start failing with `429 Too Many Requests` (`TOOMANYREQUESTS`).

<!-- more -->

The number that surfaced from the Trivy incident is **44,000 requests per minute per namespace**. When Trivy users worldwide fetched its vulnerability database from `ghcr.io/aquasecurity`, the aggregate load crossed that limit and GHCR began rejecting pulls for everything under the namespace at once, not just the one image driving the load.

Two things to keep straight:

- It counts registry **requests**, not whole image pulls. One image pull is several requests, the manifest plus a GET for each layer, so you hit the ceiling with well under 44,000 actual pulls.
- The bucket is **per minute**, so a burst hurts more than steady volume. A rollout that restarts thousands of pods at once, each pulling from the same namespace, is the classic trigger.

GitHub does not publish this figure. The [container registry docs](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry) only state a 10 GB per-layer size limit and a 10 minute upload timeout, no pull rate limit. The 44,000 number comes from the Trivy discussion, attributed to GHCR's current limit, so treat it as an undocumented, moving number, not an SLA.

To avoid GHCR ratelimit, pre-pull images to nodes, and pin digests so you do not re-pull what you already have. For a public image you depend on at scale, mirror it into your own registry rather than hitting the origin namespace on every rollout.

Docs: [Working with the Container registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry). The 44,000/min/namespace figure: [aquasecurity/trivy#8009](https://github.com/aquasecurity/trivy/discussions/8009).
