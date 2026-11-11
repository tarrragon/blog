---
title: "API Gateway"
date: 2026-04-24
description: "說明外部流量如何先收斂到一層可集中控制的入口"
weight: 132
---

API Gateway 的核心概念是「把對外流量先收斂到一層可集中控制的入口」。它負責把 client 的 request 轉成後端可處理的路由與共同政策，常見責任包括路由、身份驗證、節流、標頭補寫、版本切換與觀測欄位傳遞。 可先對照 [Request Routing](/backend/knowledge-cards/request-routing/)。

## 跟其他概念的關係

API Gateway 位在 client 與多個 backend service 之間，通常介於 load balancer 和 application 之間，作為外部入口的統一控制點，並常與 [Request Routing](/backend/knowledge-cards/request-routing/) 一起決定流量要導向哪個後端。

## 可觀察訊號

系統需要 API Gateway 的訊號是：

- 多個服務共享同一個對外入口
- 想把 auth、rate limit、request id、[Request Routing](/backend/knowledge-cards/request-routing/) 集中處理
- 希望在不改每個 service 的情況下調整入口行為

## 接近真實網路服務的例子

公共 API、行動 app、合作夥伴整合或多租戶入口常會先經過 API Gateway，再導向對應 service、internal endpoint 或特定版本路由。

## 判斷條件與後果

API Gateway 只做流量入口治理（路由、身份驗證、節流、標頭補寫）時，這些共同政策集中在一處，調整入口行為不必改每個 service；核心業務邏輯放進 gateway 時，業務規則分散在 gateway 與各個 service 兩處，改一條規則要兩邊一起改、一起部署，gateway 變成難以維護的分散型控制層。所以 gateway 能做與不能做的事，在設計時就寫明。

這條邊界有一個常被忽略的後果：gateway 讀得到的只有 transport 層看得見的東西。錯誤改放進酬載、status 恆定為 200 之後，gateway 的 retry、快取與健康判定全部依據錯誤的回應做出，而它沒有機制發現這件事（見 [錯誤格式之爭](/backend/11-api-design/error-format-debate/)）。限流的對外語意與 429 承諾見 [11.9 對外流量語意](/backend/11-api-design/external-traffic-semantics/)。
