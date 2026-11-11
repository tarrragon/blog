---
title: "Partial Failure"
date: 2026-04-23
description: "說明分散式系統中部分依賴失效時如何保留整體可用性"
weight: 51
---

Partial failure 的核心概念是「系統的一部分失效，但其他部分仍然可以運作」。分散式系統很少整體同時成功或同時失敗；更常見的是某個區域、依賴、partition、consumer 或資料副本出問題。 可先對照 [Partition](/backend/knowledge-cards/partition/)。

## 跟其他概念的關係

Partial failure 是降級、fallback、circuit breaker、failover 與 observability 的共同前提。設計要先承認某些功能會局部失效，再定義核心功能如何保留。 可先對照 [Partition](/backend/knowledge-cards/partition/)。

## 可觀察訊號與例子

系統需要 partial failure 設計的訊號是單一依賴失效會拖慢整體頁面。商品頁中推薦服務失效時，頁面仍可顯示商品資訊與購買按鈕；推薦區可以使用 fallback 或暫時空白。

## 判斷條件與後果

Partial failure 的判斷對象是某一個依賴失效時，哪些功能還能運作。核心路徑與輔助路徑沒有分開時，輔助依賴（商品頁的推薦服務）失效或變慢會拖慢整頁，商品資訊與購買按鈕跟著出不來，局部故障被放大成整體故障；分開之後，推薦區改用 fallback 或暫時空白，核心路徑照常回應。觀測資料只有整體的錯誤率與延遲時，局部故障被平均進整體的數字，看不出壞的是哪個依賴、哪個 tenant 或哪個 region；按依賴、功能區塊、tenant、region 或 endpoint 拆開的觀測資料，才顯示得出故障範圍。
