---
title: "Outbound Tunnel"
date: 2026-06-18
description: "反向隧道把出站連線轉成可達入口、與傳統 port-forward 的責任倒轉"
weight: 350
tags: ["backend", "deployment", "tunnel", "knowledge-card"]
---

Outbound tunnel 是一種入口形態：本機進程主動對外連到邊緣節點，把流量沿反向隧道帶回來，路由器零開 port、對公網零入站面。跟傳統 port-forward（從外往內開 port）的責任方向相反 — 連線由內部發起、外部只能沿已建立的隧道回來。與 [load balancer](/backend/knowledge-cards/load-balancer/) 的責任方向不同：LB 假設 instance 有公開可達位址，tunnel 由內部主動外連。

## 概念位置

Outbound tunnel 位在本機進程與公網之間，取代傳統的 port-forward 或 [load balancer](/backend/knowledge-cards/load-balancer/) 入口。常與 [TLS / mTLS](/backend/knowledge-cards/tls-mtls/) 搭配保護隧道內的傳輸安全，認證則疊在 tunnel 之後由 [authentication middleware](/backend/knowledge-cards/authentication-middleware/) 處理。

常見實作包括 cloudflared（綁 Cloudflare 邊緣）和 Tailscale（WireGuard mesh VPN）。隧道網址是位址、不是密碼 — 認證必須疊在 tunnel 之後。

深入：[5.10 Outbound Tunnel 入口與生命週期](/backend/05-deployment-platform/outbound-tunnel-entry/)。選型案例：[7.C11 Tailscale vs Cloudflare Tunnel](/backend/07-security-data-protection/cases/remote-shell-access-tailscale-vs-cloudflare-tunnel/)。
