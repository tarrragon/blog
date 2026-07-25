---
title: "動靜分離（Static / Dynamic Content Separation）"
date: 2026-07-20
description: "決定入口層或 reverse proxy 怎麼分配請求時，用動靜分離把不需要應用邏輯的靜態資源直接回掉、只把動態請求轉給應用伺服器"
weight: 51
tags: ["infra", "knowledge-cards"]
---

動靜分離指入口層把靜態資源（圖片、CSS、JS、字型）直接從檔案系統或快取回應、只把需要應用邏輯的動態請求轉發給應用伺服器的分流做法。它是 [Reverse Proxy](/infra/knowledge-cards/reverse-proxy/) 這一層最具體的職責之一，目的是把應用伺服器的算力集中在真正需要它的請求上。

## 概念位置

動靜分離坐落在 reverse proxy 的路由職責裡，跟 TLS 終結、負載分散、健康檢查並列。它跟 [nginx](/infra/knowledge-cards/nginx/) 的關係是實作面——nginx 用 `try_files` 走檔案、`proxy_pass` 轉後端，把兩類請求在設定裡分開。共享主機時代 Apache 加 mod_php 把動靜都吃在同一個 process、動靜分離是隱形預設；自管環境要明確劃出哪些路徑走檔案、哪些走後端。

## 可觀察訊號與例子

一個載入 50 個靜態資源、只有 1 個動態 API 呼叫的頁面，做了動靜分離後應用伺服器只需要處理那 1 個請求，其餘 50 個由 reverse proxy 直接回掉。判讀訊號：應用伺服器的 CPU 被大量靜態檔案請求佔用、或 access log 顯示 PHP / Node process 在回應 `.css`、`.js`——代表動靜沒有分離、算力花在不需要它的請求上。

## 判讀方式

動靜分離的邊界是「這個請求需不需要應用邏輯才能回應」。靜態資源在不同環境有不同的回應層：單機由 nginx 從檔案系統回、雲端可以再往外推到 CDN 在邊緣回。分離的層次越靠外、應用伺服器的負載越低，代價是快取失效的複雜度上升。它在入口責任鏈裡的定位、以及跟 CDN 邊緣回應的分層，在[流量入口層](/infra/03-network-foundation/traffic-entry-layer/)展開。
