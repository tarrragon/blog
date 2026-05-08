---
title: "1.3 transaction 與一致性邊界"
date: 2026-04-23
description: "整理 transaction、retry 與 isolation"
weight: 3
tags: ["backend", "database", "transaction"]
---

交易邊界（transaction boundary）的核心責任是定義哪些資料變更必須一起成立。資料庫交易的價值在於讓同一個業務動作可以被明確提交、明確回退、明確重試。

## 邊界先於語法

交易邊界先從業務動作切分，再回到 SQL。建立訂單、扣庫存、寫付款狀態是一個動作；更新推薦分數、寫審計摘要、送通知事件屬於不同節奏，適合拆成後續流程。

當同一個動作內同時包含高延遲外部呼叫，交易範圍會直接放大鎖持有時間。穩定做法是把交易內責任收斂在「需要同時成功」的資料集合，讓外部呼叫或延伸副作用透過 queue/outbox 交給後續流程。

## isolation 與 retry 的關係

[isolation level](/backend/knowledge-cards/isolation-level/) 的責任是定義交易彼此可見性。`read committed` 在高併發寫入下可維持一般業務一致性；`repeatable read` 與 `serializable` 提供更強約束，同時提高鎖競爭與重試頻率。

併發交易的常見結果是 deadlock 或 serialization failure。這些結果代表資料庫在保護一致性，應用層需要把它視為可重試路徑：重試次數有上限、重試間隔有抖動、重試前提是動作可重入。

## 服務情境

checkout 建單流程可以拆成兩層邊界。第一層是交易層：建立訂單主表與訂單項目、扣減可售庫存、寫入付款待確認狀態。第二層是延伸層：寄通知、同步 CRM、觸發分析事件。第一層要求即時一致，第二層要求最終可達。

這種切法讓交易控制面和非同步控制面各自穩定：交易層關注鎖、隔離與回退；非同步層關注投遞、重試與補償。

## 判讀訊號

| 訊號                                     | 判讀重點                       | 對應動作                                |
| ---------------------------------------- | ------------------------------ | --------------------------------------- |
| deadlock rate 升高                       | 交易範圍過大或鎖順序不一致     | 統一更新順序、縮小 transaction 範圍     |
| transaction duration 在尖峰時段上升      | 交易內含慢查詢或外部依賴       | 將外部呼叫移出交易、補索引與查詢計畫    |
| retry 成功率下降                         | 重試條件與業務冪等假設不一致   | 補 idempotency key、調整 retry 邏輯     |
| rollback 後仍出現業務狀態殘留            | 邊界切分和副作用落點未對齊     | 將副作用統一移到 outbox / consumer 路徑 |
| 交易內讀寫跨多資料域導致 contention 爆發 | 業務聚合邊界與資料模型邊界衝突 | 重新切 aggregate 與拆分熱點資料結構     |

## 常見誤區

交易保護的是一致性，不是吞吐量最大化。把過多步驟包進單一交易，會同時放大鎖競爭與回退成本。把交易切成可驗證的業務單位，能讓高併發下的可預期性更高。

重試保護的是暫時性失敗，不是所有失敗。沒有冪等保護的重試會放大副作用，特別是金流、庫存、配額這類正式狀態。

## 案例回寫

交易邊界可用 [GitHub 2018 Oct21 MySQL Topology Incident](/backend/08-incident-response/cases/github/2018-oct21-mysql-topology-incident/) 做回寫。先看事件中的主從切換與恢復順序，再回到本章判讀三件事：哪些變更必須同交易成功、哪些副作用應拆到 outbox、哪些錯誤屬於可重試而非立即回退。

若事件出現資料已寫入但外部流程落後，或重試後副作用重複，先收斂本章的邊界切分與重試前提，再同步更新 [3.3 outbox pattern](/backend/03-message-queue/outbox-pattern/) 與 [3.4 consumer 設計](/backend/03-message-queue/consumer-design/)。

## 跨模組路由

交易邊界設計會直接影響後續模組的可操作性。

1. 與 03 的交接：交易外副作用透過 [outbox pattern](/backend/knowledge-cards/outbox-pattern/) 與 consumer 落地。
2. 與 04 的交接：交易失敗需要對齊 [Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 的查詢與證據欄位。
3. 與 06 的交接：高風險交易變更納入 [Release Gate](/backend/06-reliability/release-gate/) 與 [Migration Safety](/backend/06-reliability/migration-safety/)。
4. 與 08 的交接：交易層回退或 fail-forward 判斷記錄到 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 下一步路由

要把交易與資料演進放在同一路徑看，接著讀 [1.6 資料庫轉換實作](/backend/01-database/database-migration-playbook/) 與 [6.11 Migration Safety](/backend/06-reliability/migration-safety/)。要把交易外副作用接到非同步流程，接著讀 [3.3 outbox pattern](/backend/03-message-queue/outbox-pattern/)。
