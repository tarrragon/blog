---
title: "Request Routing"
date: 2026-04-24
description: "說明入口流量如何依規則被導向不同服務或處理路徑"
weight: 133
---

Request Routing 的核心概念是「根據 request 的特徵，決定它應該被送到哪個服務或哪條處理路徑」。它處理的是入口層的分派規則，而不是訊息 broker 內部的 routing rule。 可先對照 [API Gateway](/backend/knowledge-cards/api-gateway/)。

## 跟其他概念的關係

Request Routing 位在 client、[API Gateway](/backend/knowledge-cards/api-gateway/)、[Load Balancer](/backend/knowledge-cards/load-balancer/) 與 application 之間。它通常依 host、path、header、method、tenant、版本或地區決定流量走向。

## 可觀察訊號

系統需要 request routing 的訊號是：

- 同一個對外入口要支援多個服務或版本
- 不同路徑需要不同安全政策、觀測欄位或後端處理
- 需要在不改 client 的情況下調整入口分派

## 接近真實網路服務的例子

`/api/v1` 與 `/api/v2` 導向不同版本服務、依 tenant 送到不同區域、依 path 導向不同內部服務，或把健康流量從一組 instance 切到另一組，都屬於 request routing。

## 判斷條件與後果

Request Routing 的判斷對象是每一個進入入口的 request 是否被確定地送到一個目標。兩條規則的匹配條件重疊而優先順序沒有定義時，request 送到哪個服務取決於規則的評估順序，跟設計的意圖可能不同；沒有預設路徑時，不匹配任何規則的 request 直接得到錯誤回應；規則改錯而沒有回復方式時，錯誤的分派要等新規則寫好、上線之後才停止。依業務狀態決定處理方式的邏輯寫進 routing 規則時，入口設定要跟著業務改版，同一段業務邏輯分散在 gateway 設定與服務程式兩處。
