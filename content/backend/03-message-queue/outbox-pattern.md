---
title: "3.3 outbox pattern 與發佈一致性"
date: 2026-04-23
description: "把 transaction 與 event publish 分離"
weight: 3
tags: ["backend", "message-queue", "outbox"]
---

這一章處理 [transaction](/backend/knowledge-cards/transaction/) 與訊息發佈之間的一致性問題，後續可以再延伸到 polling、relay 與 failure recovery。

外部發件箱模式（[outbox pattern](/backend/knowledge-cards/outbox-pattern/)）的核心責任是讓資料提交與事件發布在失敗時保持可恢復一致。它把重複發布轉成可判讀、可去重、可補償的治理問題。

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

## Self-managed vs Managed broker 的長期 TCO

Broker 選型本質是 long-term TCO 決策、需評估雲端費用 + 工程稅 + 治理負擔三層成本。Self-managed Kafka 的容量規劃 + broker 數量 + 副本因子 + disk + ZooKeeper / KRaft 治理是長期工程 tax、每次擴容是工程專案。

對應 [9.C9 Spotify Kafka → Pub/Sub Migration](/backend/09-performance-capacity/cases/spotify-kafka-to-pubsub-migration-gcp/) — Spotify 從自管 Kafka 遷到 Google Cloud Pub/Sub、動機是 *容量規劃的工程成本* 在 sustained growth 下變得不划算、非 Kafka 效能不足。對 7500 萬用戶的事件交付系統、把 broker 容量規劃跟運維負擔卸給 vendor、釋放工程團隊 capacity。

**TCO 評估的真實成本項**（9.C9 case 列前 4 項 + 雲端費用、第 5 項屬跨案例綜合）：

- **Broker 雲端費用**：明面成本、相對小
- **容量規劃工程**：每季 partition planning、每年容量擴張專案
- **故障處理人力**：broker 故障 oncall、ZooKeeper / KRaft 故障診斷
- **升級遷移成本**：Kafka 每個 major version 升級是專案
- **跨團隊治理**（從 3.C6 Uber 跨案例補充）：規模化後的 multi-tenant 隔離、quota 管理、observability 建設

判讀含義：Self-managed Kafka 在中小團隊可能比 Pub/Sub 便宜（雲端費用低）；但規模化後人力成本壓過雲端費用差、managed service 反而划算。對應 [3.C2 VMware Tanzu Kafka → MSK](/backend/03-message-queue/cases/vmware-kafka-to-msk/) 同樣是「自管 → managed」的決策。

**Managed service 的取捨**：

- Pub/Sub 自動 scaling、伴隨 vendor lock-in、cost-per-message 累積、message ordering / latency 特性跟 Kafka 差異
- 業務語意對映（Kafka partition / offset / consumer group 在 Pub/Sub 對映成 subscription / ordering key / message attribute）需重新校準、見 [3.7 跨 broker 業務語意對映](/backend/03-message-queue/event-contract-replay-boundary/)
- 遷移本身需驗證業務語意 — 對應 [1.7 schema migration rollout evidence](/backend/01-database/schema-migration-rollout-evidence/) 的同類流程

## Broker 遷移的階段流程

對應 [9.C9 Spotify](/backend/09-performance-capacity/cases/spotify-kafka-to-pubsub-migration-gcp/) — broker 遷移屬高併發容量工程、需維持 producer 連續寫入、保證 message 不丟。Spotify case 列三階段（dual write → shadow → cutover）、本章補第四階段（Decommission）作為清理收尾。replay 模型差異見 [3.6 Replay 跟 Idempotency 共設計](/backend/03-message-queue/processing-recovery-semantics/)。

1. **Dual-write**：producer 同時寫兩個 broker、確保 cutover 前新 broker 有完整資料
2. **Shadow consume**：新 broker 有獨立 consumer group 消費、驗證業務結果跟舊 broker 一致
3. **Cutover**：流量逐步切到新 broker、保留舊 broker 為 fallback
4. **Decommission**（本章補充、case 未明文）：確認新 broker 穩定後關掉舊 broker、清理舊架構

遷移期容量規劃含義：

- Dual-write 期間 broker 雙倍流量（writer side）
- Shadow consume 期間 consumer 雙倍負載（reader side）
- 業務驗證（mismatch tracking）期間有額外的對帳工作量

跟 [1.12 大規模 DB 遷移](/backend/01-database/large-scale-db-migration/) 是同類流程、流程細節跟 evidence chain 可互相參考。

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
