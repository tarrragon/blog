---
title: "DNS"
date: 2026-06-26
description: "Domain Name System — 把域名轉成 IP 位址的系統，以及 A record、CNAME、NS、TTL 的角色"
weight: 28
tags: ["infra", "knowledge-cards"]
---

DNS（Domain Name System）是把人類可讀的域名（`example.com`）轉成機器可達的 IP 位址（`93.184.216.34`）的分散式查詢系統。瀏覽器輸入網址後，作業系統先查本地快取、再逐層查詢 DNS server，最終拿到 IP 才能建立連線。DNS 也是 [SSL/TLS](/infra/knowledge-cards/ssl-tls/) 憑證網域驗證依賴的機制之一。

## 概念位置

DNS 在 infra 裡扮演「服務的門牌」角色。平台遷移、環境切換、TLS 憑證驗證都經過 DNS。[ALB](/infra/knowledge-cards/alb/) 或 CDN 前面通常掛一層 DNS record 作為穩定入口——IP 會隨資源重建而變，DNS 名稱不變。

## 常見的記錄類型

| 類型  | 指向什麼              | 典型用途                         |
| ----- | --------------------- | -------------------------------- |
| A     | IPv4 位址             | 主要的域名 → IP 對應             |
| AAAA  | IPv6 位址             | IPv6 環境                        |
| CNAME | 另一個域名            | 別名（`www` → `example.com`）    |
| NS    | 負責管理的 DNS server | 子域委派（dev.example.com）      |
| MX    | 郵件伺服器            | email routing                    |
| TXT   | 任意文字              | SPF / DKIM / 域名驗證（ACM）     |
| Alias | AWS 特有，指向 ALB 等 | 跟 A record 等效但支援 zone apex |

## 可觀察訊號

平台遷移時 DNS 切換是最後一步也是最不可控的一步——TTL（Time To Live）決定舊記錄被各地 DNS resolver 快取多久。TTL 300 秒代表切換後最多 5 分鐘全部 client 會指向新 IP；TTL 86400（1 天）代表最慢要等一天。遷移前 48 小時先降 TTL 到 300 秒，讓快取過期後所有 resolver 都拿到短 TTL 版本，切換時才能快速生效。

## 設計責任

DNS 設定要決定：誰管這個域名的 zone（Route 53 / Cloudflare / 域名商）、子域怎麼委派（dev / staging 用 NS delegation 交給不同 zone）、TTL 設多少（平常 3600 秒夠用、遷移前降到 300）。ACM 的 DNS 驗證也依賴 DNS——建立 TXT 或 CNAME 記錄證明域名歸屬。

## 鄰卡

- [ALB](/infra/knowledge-cards/alb/) — DNS 記錄通常指向 ALB 作為流量入口
- [SSL/TLS](/infra/knowledge-cards/ssl-tls/) — TLS 憑證的 DNS 驗證依賴 DNS record
- [流量入口層](/infra/03-network-foundation/traffic-entry-layer/) — DNS 作為責任鏈第一段（門牌、只在連線前查一次、不承載流量）的定位
