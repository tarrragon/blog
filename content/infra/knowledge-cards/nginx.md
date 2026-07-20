---
title: "nginx"
date: 2026-06-26
description: "高效能 Web Server 與 Reverse Proxy，以集中設定檔取代 Apache 的 .htaccess 分散設定"
weight: 33
tags: ["infra", "knowledge-cards"]
---

nginx 是高效能的 Web Server 和 [Reverse Proxy](/infra/knowledge-cards/reverse-proxy/)，以非同步事件驅動架構處理大量並發連線。它在全球 web server 市場佔有率與 Apache 並列前二，新部署的伺服器多數選 nginx。

## 概念位置

nginx 在 infra 裡常見的角色有三種：作為 reverse proxy 把請求轉給後端應用（Node.js、PHP-FPM、Python WSGI）、作為靜態檔案伺服器、作為 TLS 終結點處理 HTTPS。[ALB](/infra/knowledge-cards/alb/) 在雲端環境承擔了部分 nginx 的職責（負載平衡、TLS 終結），但 VPS 環境裡 nginx 仍然是標準選擇。

## 跟 Apache 的關鍵差別

| 面向        | nginx                              | Apache                               |
| ----------- | ---------------------------------- | ------------------------------------ |
| 設定模式    | 集中式（`/etc/nginx/` 下的設定檔） | 支援 .htaccess 分散式設定            |
| 並發模型    | 事件驅動、非阻塞                   | 預設 prefork（每個請求一個 process） |
| PHP 整合    | 透過 FastCGI（PHP-FPM）            | mod_php（直接嵌入）或 FastCGI        |
| URL rewrite | `location` + `rewrite` 區塊        | `.htaccess` 的 `RewriteRule`         |

## 可觀察訊號

OS 升級或平台遷移時，如果從 Apache 換成 nginx，所有 `.htaccess` 規則要手動轉成 nginx 設定：URL rewrite、目錄保護、PHP 設定覆寫、安全標頭。nginx 沒有 `.htaccess` 的等價物——所有設定都在集中的設定檔裡，需要 reload nginx 才能生效（Apache 的 `.htaccess` 每次請求都重新讀取）。

## 設計責任

nginx 設定要決定：server block（類似 Apache 的 VirtualHost）怎麼組織、upstream 指向哪個 app server、靜態檔案的 root 路徑、TLS 憑證掛在哪裡、access log 和 error log 的路徑。設定改完跑 `nginx -t` 驗證語法後再 `nginx -s reload`。

## 鄰卡

- [.htaccess](/infra/knowledge-cards/htaccess/) — Apache 的分散設定，遷移到 nginx 時需要轉換
- [ALB](/infra/knowledge-cards/alb/) — 雲端環境裡承擔部分 nginx 職責
