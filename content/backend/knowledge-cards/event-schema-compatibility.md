---
title: "Event Schema Compatibility"
date: 2026-06-16
description: "說明 event schema 演進時，新舊 producer 與 consumer 能否互通的相容性等級"
weight: 380
---

Event schema compatibility 的核心概念是「event schema 改版後，新舊 producer 與 consumer 能否互通」。它用 forward、backward、full 三種相容性等級界定演進規則，是跨服務事件契約能安全升級的前提。 可先對照 [Delivery Semantics](/backend/knowledge-cards/delivery-semantics/)。

## 概念位置

Event schema compatibility 是事件契約的演進規則，直接影響 [processing semantics](/backend/knowledge-cards/processing-semantics/)：schema 不相容會讓 consumer 解析失敗、變成 [poison message](/backend/knowledge-cards/poison-message/)。backward 相容讓新 consumer 讀舊事件、forward 相容讓舊 consumer 讀新事件、full 兩者都要。

## 可觀察訊號與例子

producer 加一個必填欄位但未設預設值，舊 consumer 解析失敗、訊息卡在 partition；改成可選欄位或帶預設值就維持 backward 相容。Kafka 用 Schema Registry enforce compatibility level、Pub/Sub 用 schema enforcement，RabbitMQ 與 NATS 多半靠應用層約定。

## 設計責任

設計時先定相容性等級再演進 schema：高頻跨服務契約用 full 或 backward、內部單向通訊可放寬。新增欄位帶預設、刪欄位分兩步（先停用再移除），避免一次破壞性改版打掛下游。
