---
title: "Event Schema Compatibility"
date: 2026-06-16
description: "說明 event schema 演進時，新舊 producer 與 consumer 能否互通的相容性等級"
weight: 381
---

Event schema compatibility 的核心概念是「event schema 改版後，新舊 producer 與 consumer 能否互通」。它用 forward、backward、full 三種相容性等級界定演進規則，是跨服務事件契約能安全升級的前提。 可先對照 [Delivery Semantics](/backend/knowledge-cards/delivery-semantics/)。

## 跟其他概念的關係

Event schema compatibility 是事件契約的演進規則，直接影響 [processing semantics](/backend/knowledge-cards/processing-semantics/)：schema 不相容會讓 consumer 解析失敗、變成 [poison message](/backend/knowledge-cards/poison-message/)。backward 相容讓新 consumer 讀舊事件、forward 相容讓舊 consumer 讀新事件、full 兩者都要。

## 可觀察訊號與例子

producer 加一個必填欄位但未設預設值，舊 consumer 解析失敗、訊息卡在 partition；改成可選欄位或帶預設值就維持 backward 相容。Kafka 用 Schema Registry enforce compatibility level、Pub/Sub 用 schema enforcement，RabbitMQ 與 NATS 多半靠應用層約定。

## 判斷條件與後果

相容性等級要多嚴，看新舊版本的 producer 與 consumer 會並存多久。跨服務的事件契約有多個 consumer、各自的部署時程不同時，新舊版本會同時存在一段時間，等級低於 full 或 backward 時，舊版 consumer 讀不懂新版事件，或新版 consumer 讀不懂舊版事件，解析失敗的訊息成為 [poison message](/backend/knowledge-cards/poison-message/) 卡在 partition；只有一個 consumer、與 producer 同步部署的內部通訊，新舊版本並存的時間短，等級可以放寬。新增的欄位沒有預設值時，舊事件讀進新 consumer 缺那個欄位，backward 相容就此破壞；一次刪掉一個 consumer 仍在讀的欄位時，那個 consumer 立刻解析失敗，所以刪欄位分兩步，先停止使用、等所有 consumer 都不讀它，再移除。
