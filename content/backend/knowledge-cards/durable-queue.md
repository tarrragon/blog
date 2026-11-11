---
title: "Durable Queue"
date: 2026-04-23
description: "說明可持久化的 queue 如何在重啟與失敗後保留待處理工作"
weight: 145
---

Durable queue 的核心概念是「待處理工作在 process 重啟或節點故障後仍可被取回」。它把 queue 從記憶體暫存提升為可恢復的工作通道。 可先對照 [Queue](/backend/knowledge-cards/queue/)。

## 跟其他概念的關係

Durable queue 是 [queue](/backend/knowledge-cards/queue/) 與 [message persistence](/backend/knowledge-cards/message-persistence/) 的組合，常由 [broker](/backend/knowledge-cards/broker/) 提供，並搭配 [ack/nack](/backend/knowledge-cards/ack-nack/)、[retry policy](/backend/knowledge-cards/retry-policy/) 與 [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/)。

## 可觀察訊號與例子

當工作可延遲但不可遺失時，durable queue 是常見候選。例如付款後通知、對帳同步、背景轉檔。若僅需在線即時廣播，通常 [pub/sub](/backend/knowledge-cards/pub-sub/) 成本更低。

## 判斷條件與後果

Durable queue 保證的只有訊息在重啟後還在，訊息之後的去向由幾個設定決定，哪一個沒有定義，那一段就要靠人工排障。保存期限沒有定義時，處理不掉的訊息一直累積在儲存裡；重試上限沒有定義時，一則永遠失敗的訊息被反覆重送，佔住 consumer 的處理能力，原因是 broker 只知道這則訊息還沒 ack；沒有去重策略時，重啟後被再投遞的訊息會造成 [duplicate delivery](/backend/knowledge-cards/duplicate-delivery/)；沒有 queue lag 告警時，consumer 落後到工作延遲超出業務可以等的時間才被發現；沒有回復流程時，故障之後積壓的訊息怎麼重新處理要當場決定。
