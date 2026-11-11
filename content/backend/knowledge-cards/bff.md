---
title: "BFF"
date: 2026-04-23
description: "說明 Backend for Frontend 如何聚合下游服務並服務特定客戶端"
weight: 157
---

BFF 的核心概念是「為特定前端體驗提供專用後端聚合層」。它可降低前端多次呼叫與資料拼裝成本。 可先對照 [Blast Radius](/backend/knowledge-cards/blast-radius/)。

## 跟其他概念的關係

常見於 Web 與 App 需求差異明顯時，BFF 會整合多個下游 API 並回傳前端所需形狀。 可先對照 [Blast Radius](/backend/knowledge-cards/blast-radius/)。

## 判斷條件與後果

BFF 整合多個下游 API，一個前端請求的延遲與可用性因此取決於它呼叫的全部下游。聚合邊界沒有劃定時，BFF 逐漸收進業務邏輯與更多下游呼叫，變成所有前端畫面共用的單點；沒有逐一下游的超時控制時，最慢的下游決定整個回應的延遲；沒有降級策略時，一個非必要的下游失敗就讓整頁回傳錯誤；有降級策略時，同樣的失敗只讓頁面少一塊內容。快取策略決定重複的聚合請求是否每次都打到下游，沒有快取時，下游的負載隨前端流量同比例成長。
