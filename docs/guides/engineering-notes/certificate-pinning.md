---
tags:
  - security
  - tls
  - certificates
---

# Certificate pinning: which to use

Short-lived certificates are coming (CA/Browser Forum ballot SC-081v3), and they
break the most common form of pinning.

## Certificate lifetimes are shrinking

Ballot SC-081v3 was unanimously approved on April 11, 2025 (all four major
browser vendors plus 25 CAs in favor, none against). It is a binding requirement
for every publicly-trusted CA:

| From | Max public TLS certificate lifetime |
|------|-------------------------------------|
| Today | 398 days |
| March 2026 | 200 days |
| March 2027 | 100 days |
| March 2029 | 47 days |

By 2029 a pinned leaf certificate rotates roughly every six weeks.

## The three pinning levels

| Approach | What you pin | Survives renewal | Survives CA change | Operational cost |
|----------|--------------|------------------|--------------------|------------------|
| Leaf | the exact server certificate | No | No | Very high |
| SPKI | SHA-256 of the public key (SubjectPublicKeyInfo) | Yes, if the key is reused | Yes | Low |
| Root CA | the root authority in the chain | Yes | No (same root) | Lowest |

## Rule of thumb

- Never pin the **leaf** certificate. It breaks on every renewal, which under
  47-day certificates means a scheduled outage every few weeks.
- Pin **SPKI** or the **Root CA** instead, and always ship at least one
  **backup pin** so a planned key rotation does not lock clients out.
- You may not need pinning at all if you already have Certificate Transparency,
  automated certificate lifecycle management, and strong TLS with forward
  secrecy. Pin only against a specific threat.

## Sources

- Cloudflare: [Why certificate pinning is outdated](https://blog.cloudflare.com/why-certificate-pinning-is-outdated/)
- DigiCert: [TLS certificate lifetimes will reduce to 47 days](https://www.digicert.com/blog/tls-certificate-lifetimes-will-officially-reduce-to-47-days)
- CA/Browser Forum ballot SC-081v3
