---
title: "SSL / TLS"
date: 2026-06-26
description: "加密 client 與 server 之間通訊的協定，讓 HTTPS 成為可能。TLS 是 SSL 的後繼者，但 SSL 憑證的稱呼仍廣泛使用"
weight: 29
tags: ["infra", "knowledge-cards"]
aliases: ["/infra/knowledge-cards/ssl-tls/"]
---

TLS（Transport Layer Security）加密 client 與 server 之間的通訊，防止中間人竊聽或竄改。HTTPS 就是 HTTP 加上 TLS 加密層。SSL 是 TLS 的前身、所有版本都已被棄用，但「SSL 憑證」這個稱呼仍然廣泛使用——實際上指的是 TLS 憑證。TLS 憑證的核發常搭配 [DNS](/devops/infra/knowledge-cards/dns/) 驗證持有權。

## 跟其他概念的關係

TLS 在 infra 裡負責「傳輸安全」。[ALB](/devops/infra/knowledge-cards/alb/) 的 HTTPS listener 需要掛一張 TLS 憑證；ACM（AWS Certificate Manager）提供免費的憑證申請與自動續期；Let's Encrypt 是跨平台的免費 CA（Certificate Authority，憑證簽發機構）。

## 可觀察訊號

TLS 憑證有到期日。過期的憑證會讓瀏覽器顯示安全警告、部分 client 直接拒絕連線。ACM 管理的憑證會自動續期（前提是 DNS 驗證記錄仍然存在）；手動上傳的憑證需要人工追蹤到期日。接手維運時要確認：憑證的簽發者是誰、到期日是什麼時候、續期是自動還是手動。

用 CLI 查看遠端憑證資訊：

```bash
echo | openssl s_client -connect example.com:443 2>/dev/null | openssl x509 -noout -dates -issuer
```

## 判斷條件與後果

TLS 憑證過期會讓瀏覽器顯示安全警告、部分 client 直接拒絕連線，而續期能不能自動完成，看憑證的來源與驗證網域持有權的方式。憑證來自 ACM 時免費而且自動續期，前提是 DNS 驗證記錄仍然存在，代價是它只能掛在 AWS 的服務上；來自 Let's Encrypt 時同樣免費而且跨平台，續期要靠主機上的用戶端定期執行。驗證方式是 DNS 時，續期整段由程式完成；是 email 時，每一次續期都要有人收信點確認，那個人不在或信箱換了，憑證就照到期日過期。一張憑證要同時涵蓋 `example.com` 與 `*.example.com` 時，用多域名的 SAN 憑證，否則其中一個網域的連線會出現憑證不符的警告。HTTP 沒有強制跳轉到 HTTPS 時，用 `http://` 進來的使用者走的是沒有加密的連線，憑證再正確也保護不到他。

## 鄰卡

- [DNS](/devops/infra/knowledge-cards/dns/) — TLS 憑證的 DNS 驗證依賴 DNS record
- [ALB](/devops/infra/knowledge-cards/alb/) — HTTPS listener 需要掛 TLS 憑證
- [流量入口層](/devops/infra/03-network-foundation/traffic-entry-layer/) — TLS 終結放在責任鏈哪一層（入口終結 / 透傳 / 重新加密）的架構選擇
