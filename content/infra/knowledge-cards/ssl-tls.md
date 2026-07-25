---
title: "SSL / TLS"
date: 2026-06-26
description: "加密 client 與 server 之間通訊的協定，讓 HTTPS 成為可能。TLS 是 SSL 的後繼者，但 SSL 憑證的稱呼仍廣泛使用"
weight: 29
tags: ["infra", "knowledge-cards"]
---

TLS（Transport Layer Security）加密 client 與 server 之間的通訊，防止中間人竊聽或竄改。HTTPS 就是 HTTP 加上 TLS 加密層。SSL 是 TLS 的前身、所有版本都已被棄用，但「SSL 憑證」這個稱呼仍然廣泛使用——實際上指的是 TLS 憑證。TLS 憑證的核發常搭配 [DNS](/infra/knowledge-cards/dns/) 驗證持有權。

## 概念位置

TLS 在 infra 裡負責「傳輸安全」。[ALB](/infra/knowledge-cards/alb/) 的 HTTPS listener 需要掛一張 TLS 憑證；ACM（AWS Certificate Manager）提供免費的憑證申請與自動續期；Let's Encrypt 是跨平台的免費 CA（Certificate Authority，憑證簽發機構）。

## 可觀察訊號

TLS 憑證有到期日。過期的憑證會讓瀏覽器顯示安全警告、部分 client 直接拒絕連線。ACM 管理的憑證會自動續期（前提是 DNS 驗證記錄仍然存在）；手動上傳的憑證需要人工追蹤到期日。接手維運時要確認：憑證的簽發者是誰、到期日是什麼時候、續期是自動還是手動。

用 CLI 查看遠端憑證資訊：

```bash
echo | openssl s_client -connect example.com:443 2>/dev/null | openssl x509 -noout -dates -issuer
```

## 設計責任

TLS 設定要決定：憑證從哪裡來（ACM 免費但只能用在 AWS 服務上、Let's Encrypt 免費且跨平台）、驗證方式（DNS 驗證適合自動化、email 驗證較手動）、是否需要多域名的 SAN 憑證（一張憑證涵蓋 `example.com` + `*.example.com`）、HTTP → HTTPS 的強制跳轉怎麼設。

## 鄰卡

- [DNS](/infra/knowledge-cards/dns/) — TLS 憑證的 DNS 驗證依賴 DNS record
- [ALB](/infra/knowledge-cards/alb/) — HTTPS listener 需要掛 TLS 憑證
- [流量入口層](/infra/03-network-foundation/traffic-entry-layer/) — TLS 終結放在責任鏈哪一層（入口終結 / 透傳 / 重新加密）的架構選擇
