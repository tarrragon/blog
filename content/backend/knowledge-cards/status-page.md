---
title: "Status Page"
tags: ["狀態頁", "Status Page"]
date: 2026-05-02
description: "說明事故期間對外狀態頁如何承接可用性承諾"
weight: 314
---

Status page 的核心概念是「把事故影響、處理節奏與回復進度公開成單一對外契約」。它和 [incident communication channel](/backend/knowledge-cards/incident-communication-channel/) 與 [incident severity](/backend/knowledge-cards/incident-severity/) 一起決定外部看到的真實版本。

## 跟其他概念的關係

Status page 位在 [incident communication channel](/backend/knowledge-cards/incident-communication-channel/)、[stakeholder mapping](/backend/knowledge-cards/stakeholder-mapping/) 與 [post-incident-review](/backend/knowledge-cards/post-incident-review/) 之間。它把內部節奏轉成客戶可讀的更新，並把 ETA、影響範圍與下一次更新時間固定下來。

## 可觀察訊號與例子

系統需要 status page 的訊號是事故已經影響外部使用者，但內部的戰情室節奏還不能直接交給客戶。常見例子包括區域性 outage、身份平台失效、外部供應商中斷與多租戶服務退化。

## 判斷條件與後果

客服逐一回覆用的內部版本比對外狀態頁多一欄「對客戶的說法」，見 [8.24 客服回報的處理](/backend/08-incident-response/support-escalation-and-engineering-reply/#客服當場答覆時用的資訊)。

Status page 的更新頻率、發佈責任、嚴重度標示、影響範圍與下一次更新時間是事故開始之前就訂好的項目，事故當下才決定時，對外的更新會出現這幾種狀態：沒有指定由誰發佈時，更新停在第一則公告；沒有寫出下一次更新時間時，客戶只能反覆刷新頁面或改問客服；嚴重度與影響範圍沒有固定的標示方式時，同一次事故在前後幾則更新裡讀起來輕重不一。這幾項是對外承諾的最小集合，內容照公關稿的標準修飾時，客戶拿自己遇到的故障對照公告，看到兩者對不上，之後的公告也失去可信度。Status page 跟主服務放在同一個[失效域](/backend/knowledge-cards/failure-domain/)（同一個 domain、同一套 infra 或 DNS）時，主站停擺的那一刻狀態頁也連不上，原因是兩者依賴同一組元件，見 [4.25 觀測共命運失效](/backend/04-observability/observability-shared-fate/)。
