---
title: "Service Endpoint"
date: 2026-04-23
description: "說明服務如何對外暴露可被路由與存取的入口"
weight: 127
---

Service Endpoint 的核心概念是「外部請求進入服務的明確位置」。它是網路流量進入應用程式邊界的地址、路徑或命名位置。 可先對照 [Request Routing](/backend/knowledge-cards/request-routing/)。

## 跟其他概念的關係

Service Endpoint 位在 client、load balancer、WAF 與 application 之間，是服務對外暴露能力的入口界面，常與 [Request Routing](/backend/knowledge-cards/request-routing/) 一起決定流量如何進入。

## 可觀察訊號

系統需要 service endpoint 分級的訊號是不同入口承擔的風險不同。公開 API、管理入口、診斷入口與內部入口的流量來源、權限要求與失敗後果都不一樣。

## 接近真實網路服務的例子

公開 API 需要穩定的 request/response 合約；[Public API Endpoint](/backend/knowledge-cards/public-api-endpoint/) 需要更高的相容性與文件品質；[Admin Endpoint](/backend/knowledge-cards/admin-endpoint/) 需要更高權限與來源限制；[Diagnostic Endpoint](/backend/knowledge-cards/diagnostic-endpoint/) 需要避免暴露過多內部資訊；[Internal Endpoint](/backend/knowledge-cards/internal-endpoint/) 需要搭配 service discovery 與內部網路邊界。

## 判斷條件與後果

Service endpoint 的用途、可達範圍、授權層級與錯誤回應策略決定這個入口出錯時的後果。所有 HTTP 路徑都套同一組可達範圍與授權時，管理入口與公開 API 一樣從外網連得到，診斷入口的錯誤回應與公開 API 一樣詳細，原因是設定只有一組，風險最高的入口跟著風險最低的入口開放。按用途分級之後，每一級的流量來源、權限要求與失敗後果各自不同，細節分別在 [Public API Endpoint](/backend/knowledge-cards/public-api-endpoint/)、[Admin Endpoint](/backend/knowledge-cards/admin-endpoint/)、[Diagnostic Endpoint](/backend/knowledge-cards/diagnostic-endpoint/) 與 [Internal Endpoint](/backend/knowledge-cards/internal-endpoint/)。
