---
title: "域名與 HTTPS 怎麼接上"
date: 2026-07-06
description: "服務跑在一個 IP 上了、但不知道買的域名怎麼指過去、網址前面的鎖頭（HTTPS）憑證從哪來時回來讀 — 域名解析與 TLS 的最小認識"
weight: 3
tags: ["going-live", "deployment", "dns", "tls", "foundations"]
---

你的服務跑在一台有公網 IP 的機器上之後，還差兩件事才「像個正常網站」：一是讓 `example.com` 指到那個 IP（DNS），二是讓網址是 `https://` 而不是 `http://`（TLS 憑證）。這兩件都是每個上線服務的標配，但沒人明講時最容易卡住。

## 域名怎麼指到伺服器：一筆 DNS 紀錄

域名系統（DNS）是「把人記得住的名字翻成機器用的 IP」的電話簿。你在網域註冊商買下 `example.com` 後，到它（或你用的 DNS 服務）的管理介面，加一筆 **A record**：

```text
類型   名稱            值（指向）
A      example.com     203.0.113.10      ← 你伺服器的公網 IP
A      www             203.0.113.10
```

A record 就是「這個名字 → 這個 IPv4」。加完後，全世界查 `example.com` 會拿到你的 IP、連過來。幾個常見卡點：

- **改了要等生效**：DNS 有快取（TTL），改動可能幾分鐘到幾小時才全球生效，不是即時。
- **A vs CNAME**：A 指向 IP；CNAME 指向「另一個域名」（常用在指到 PaaS 給你的網址，如 `myapp.onrender.com`）。用 PaaS 時多半是設 CNAME——但裸網域 `example.com`（apex）依 DNS 規範不能掛 CNAME，只能用 A、或供應商的 ALIAS/flattening，子網域（`www`）才能 CNAME。這是 PaaS + 裸網域第一次上線的高頻卡點。
- **域名 ≠ 伺服器**：買域名跟租主機是兩件事、常在不同供應商。域名只是指標，指向哪台機器由 A/CNAME 決定。

DNS 各紀錄類型的細節見 [Infra DNS 卡](/infra/knowledge-cards/dns/)。

## HTTPS 的鎖頭從哪來：TLS 憑證

`https://` 前面那個鎖頭代表兩件事：**連線被加密**（別人竊聽不到內容）、以及**對方身分被驗證**（你連的真的是 `example.com`、不是假冒的）。做到這兩點靠的是 **TLS 憑證**——一份由受信任的憑證頒發機構（CA）簽發、證明「這個域名是這台伺服器的」的檔案。

瀏覽器內建信任一批 CA。伺服器出示 CA 簽的憑證，瀏覽器驗章通過，鎖頭就亮、連線加密。憑證怎麼運作、CA 信任鏈的細節見 [Infra SSL/TLS 卡](/infra/knowledge-cards/ssl-tls/)。

## 憑證怎麼拿：Let's Encrypt 讓它免費又自動

以前憑證要花錢買，現在 **Let's Encrypt** 這個免費 CA 讓它變成一行指令。它用 ACME 協議自動驗證「你確實控制這個域名」（通常是讓它連你的 server 或設一筆 DNS 紀錄），驗過就簽發，且能自動續期（憑證有 90 天效期）。

- **自己顧機器（VPS）**：用 `certbot` 之類的工具，指令大致是 `certbot --nginx -d example.com`——它自動取得憑證、改好 nginx 設定、排程續期。
- **用 PaaS**：平台通常自動幫你上憑證，你只要把域名指過去（設 CNAME）就有 HTTPS，完全不碰 certbot。

## TLS 在哪裡「終結」

加解密這件事通常由 app 前面的一層代勞——nginx、負載平衡器、或 CDN 負責「TLS termination」：對外收 HTTPS、解密後用普通 HTTP 轉給後面的 app。所以你 app 本身常常只講 HTTP，HTTPS 是前面那層加上去的。反向代理 / LB 承擔這類職責的細節見 [運行期維運 反向代理職責](/operations/01-load-balancing/reverse-proxy-responsibilities/)。

## 下一步

域名跟 HTTPS 接上，服務就「對外像個正常網站」了。接著是讓服務本身好部署、好搬家——見 [十二要素基線](/going-live/twelve-factor-baseline/)。用 IaC 把 DNS 與憑證納管（Route53 + ACM）的進階做法見 [Infra 核心服務](/infra/05-core-services/)。
