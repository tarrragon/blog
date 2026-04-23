---
title: "API Gateway"
date: 2026-04-24
description: "說明外部流量如何先收斂到一層可集中控制的入口"
weight: 131
---

API Gateway 的核心概念是「把對外流量先收斂到一層可集中控制的入口」。它負責把 client 的 request 轉成後端可處理的路由與共同政策，常見責任包括路由、身份驗證、節流、標頭補寫、版本切換與觀測欄位傳遞。

## 概念位置

API Gateway 位在 client 與多個 backend service 之間，通常介於 load balancer 和 application 之間，作為外部入口的統一控制點，並常與 [Request Routing](request-routing/) 一起決定流量要導向哪個後端。

## 可觀察訊號

系統需要 API Gateway 的訊號是：

- 多個服務共享同一個對外入口
- 想把 auth、rate limit、request id、[Request Routing](request-routing/) 集中處理
- 希望在不改每個 service 的情況下調整入口行為

## 接近真實網路服務的例子

公共 API、行動 app、合作夥伴整合或多租戶入口常會先經過 API Gateway，再導向對應 service、internal endpoint 或特定版本路由。

## 設計責任

設計時要明確定義 gateway 能做與不能做的事。它應承擔流量入口治理，而不應塞入核心業務邏輯，否則會變成難以維護的分散型控制層。
