---
title: "Sticky Session"
tags: ["黏性會話", "Sticky Session"]
date: 2026-04-24
description: "說明同一 client 如何在一段時間內持續命中同一個後端實例"
weight: 131
---

Sticky Session 的核心概念是「讓同一個 client、session 或 connection 在一段時間內持續命中同一個服務實例」。它是一種負載平衡策略，常用來維持本機狀態、暫存資料或未外部化 session 的可用性。 可先對照 [Stream Pipeline](/backend/knowledge-cards/stream-pipeline/)。

## 跟其他概念的關係

Sticky Session 位在 client、load balancer、application instances 與 session state 之間。它改變的是流量分派規則，不是應用邏輯本身。 可先對照 [Stream Pipeline](/backend/knowledge-cards/stream-pipeline/)。

## 可觀察訊號

系統需要 sticky session 的訊號是：

- 服務仍保存本機狀態，短期內不容易外部化
- 多步驟互動需要維持同一個後端實例
- session state 還沒移到共享儲存或快取

## 接近真實網路服務的例子

聊天室、即時遊戲、某些登入流程、需要本機暫存的舊系統，常會要求同一個使用者在 session 期間保持 sticky routing。

## 判斷條件與後果

Sticky session 把同一個 client 固定在一個 instance 上，每台 instance 的負載因此取決於分到的 session 數與這些 session 的活躍程度：重度使用者或長連線集中在某一台時，那一台先到資源上限，其他台還有餘裕。判斷鍵（cookie、session id、來源 IP）決定哪些請求算同一個 client，用來源 IP 當判斷鍵時，同一個 NAT 後面的大量使用者都被分到同一台。有效時間沒有設定時，黏著關係一直保留到 instance 下線，新加入的 instance 分不到既有的 session，擴充之後負載仍集中在舊的那幾台。被黏著的 instance 故障時，存在它本機的 session 狀態跟著消失，使用者被重新導向到別台之後要重新登入或從頭走多步驟流程。這幾種代價都來自狀態留在本機，所以 sticky session 是 session state 移到共享儲存之前的權宜做法。
