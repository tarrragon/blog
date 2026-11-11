---
title: "Retention"
date: 2026-06-22
description: "說明資料或事件保留多久，以及保留期限如何影響重放與成本"
weight: 76
tags: ["backend", "observability"]
---

Retention 的核心概念是「資料或事件在系統中保留多久」。它影響 storage cost、audit 能力、replay 能力、debug 時間窗口、合規義務與資料刪除責任，跟 [storage tiering](/backend/knowledge-cards/storage-tiering/) 與 [rollup](/backend/knowledge-cards/rollup/) 共同構成資料生命週期管理。

## 跟其他概念的關係

Retention 連接資料生命週期跟查詢能力。不同類型的資料需要不同保留期限 — log 的 debug 用途可能只需要 7 天，而要讓工程以使用者回報的請求編號逐筆查到請求，完整粒度的請求 log 要保留到涵蓋從使用者遇到錯誤到工程查 log 的時間（見 [11.16 面向終端使用者的錯誤碼與請求編號](/backend/11-api-design/end-user-error-code-and-reference-id/#log-保留期從使用者遇到錯誤到工程查-log-的時間)）、audit log 因合規要求可能需要 1 年以上、metrics 的 raw data 可能保留 15 天但 [rollup](/backend/knowledge-cards/rollup/) 保留 90 天。

Retention 跟 [storage tiering](/backend/knowledge-cards/storage-tiering/) 搭配運作 — hot tier 保留最近的高精度資料、warm / cold tier 保留較舊的低精度或歸檔資料。保留期限的設定見 [4.7 cardinality 與成本邊界](/backend/04-observability/cardinality-cost-governance/) 的保留階梯段。

## 使用情境

系統需要 retention 設計的訊號是事故排查或資料修復需要回看歷史。若 event stream 只保留 24 小時，三天前的錯誤就無法靠 replay 重建。反過來，無限保留會讓儲存成本持續成長。

## 判斷條件與後果

Retention 的長度由幾個方向相反的條件共同決定。保留越長，儲存成本隨資料量乘以時間成長，高敏感資料外洩時暴露的範圍也越大；保留越短，事後分析與 replay 的時間窗口越窄，事故後要回看的資料已經被刪掉，MQ 的 consumer 落後超過保留期時也追不回漏掉的訊息。法規可能同時給出下限與上限（合規要求的最短保留期、GDPR 要求的最長保留期），兩者對同一類資料衝突時，整個系統用一個保留期滿足不了兩邊，所以保留期依資料類型分開設定：error log 保留比 debug log 長，audit log 保留比 operational log 長。
