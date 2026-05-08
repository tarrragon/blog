---
title: "3.3 outbox pattern 與發佈一致性"
date: 2026-04-23
description: "把 transaction 與 event publish 分離"
weight: 3
tags: ["backend", "message-queue", "outbox"]
---

這一章處理 [transaction](/backend/knowledge-cards/transaction/) 與訊息發佈之間的一致性問題，後續可以再延伸到 polling、relay 與 failure recovery。

外部發件箱模式（outbox pattern）的核心責任是讓資料提交與事件發布在失敗時保持可恢復一致。它把重複發布轉成可判讀、可去重、可補償的治理問題。

## 基本流程

transaction outbox 的典型流程是：在同一資料庫交易內，同時寫入業務資料與 outbox 記錄；交易提交後，由 relay worker 讀取 outbox 並發布到 broker；發布成功後標記或刪除 outbox 記錄。

這個流程把一致性問題從「跨系統兩段提交」改成「單系統交易 + 非同步重送」，讓失敗路徑更可控。

## relay worker

relay worker 的責任是穩定發布與可恢復進度。worker 需要具備批次拉取、順序控制、重試策略與停損條件。進度管理要明確，避免重啟後漏發或重複失控。

當流量上升時，relay 吞吐會成為關鍵瓶頸。穩定做法是分 shard 處理、限制批次大小、對重試與正常發布做通道分流。

## 發布失敗與補償

發布失敗通常分為暫時性與系統性。暫時性故障走有限重試，系統性故障走隔離與告警。關鍵是保留 outbox 記錄與發布狀態，讓恢復時可重播。

duplicate publish 在 outbox 模式下屬於預期現象。消費端需要配合 idempotency 機制，確保重複事件不會產生重複業務結果。

## 判讀訊號

| 訊號                               | 判讀重點                     | 對應動作                             |
| ---------------------------------- | ---------------------------- | ------------------------------------ |
| outbox backlog 持續堆積            | relay 吞吐不足或下游故障持續 | 擴充 worker、分流重試、啟動降級流程  |
| 業務資料已更新但下游狀態延遲明顯   | 發布延遲超出可接受窗口       | 提升 relay 優先級、補告警與可視化    |
| duplicate consume 比例上升         | 重試與重播增加，去重壓力上升 | 強化 consumer idempotency 與去重儲存 |
| relay 重啟後出現漏發               | 進度標記與交易邊界設計不穩   | 收斂進度策略、補恢復測試             |
| 同步交易延遲上升且 outbox 寫入增加 | outbox 表設計與索引不足      | 調整索引與分表策略、拆分熱路徑       |

## 常見誤區

把 outbox 當作「一次解決一致性」的銀彈，會忽略消費端冪等與補償責任。outbox 保證的是發布可恢復，不是端到端結果自動正確。

把 outbox 表當一般業務表無上限累積，也會放大查詢與維護成本。需要定義保留與清理節奏，並確保稽核需求有對應方案。

## 案例回寫

outbox 一致性可用 [GitHub 2018 Oct21 MySQL Topology Incident](/backend/08-incident-response/cases/github/2018-oct21-mysql-topology-incident/) 的恢復段落回寫。先看資料寫入與下游狀態同步是否脫節，再回到本章檢查 outbox backlog、relay 進度與重播策略。
這個案例主要支撐的是「提交後發布一致性」判讀，不直接支撐 broker 的底層投遞參數；若問題是 ack/partition 策略，應回到 3.1/3.2。

當資料已提交但事件遲到，或重播後副作用重複時，先調整 relay 節流與 consumer 冪等，再把驗證證據對齊 [6.23 Verification Evidence Handoff](/backend/06-reliability/verification-evidence-handoff/)。

## 跨模組路由

1. 與 1.3 的交接：交易邊界語意回到 [transaction 與一致性邊界](/backend/01-database/transaction-boundary/)。
2. 與 3.2 的交接：發布後重試與隔離回到 [durable queue 與重試策略](/backend/03-message-queue/durable-queue/)。
3. 與 3.4 的交接：消費冪等與重播回到 [consumer 設計與去重](/backend/03-message-queue/consumer-design/)。
4. 與 6.12 的交接：一致性驗證與重播演練回到 [Idempotency 與 Replay 驗證](/backend/06-reliability/idempotency-replay/)。
5. 與 8.19 的交接：發布故障決策回到 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 下一步路由

要從 outbox 延伸到消費恢復，接著讀 [3.4 consumer 設計與去重](/backend/03-message-queue/consumer-design/)。要看 queue 切換失敗時的一致性風險，接著讀 [3.C9 反例](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/)。
