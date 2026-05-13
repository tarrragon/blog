---
title: "3.8 Queue Consumer Retry 與 Replay Handoff（實作示範）"
date: 2026-05-11
description: "以 order_created consumer 示範 queue 路徑如何交付 idempotency evidence、DLQ handling、replay runbook 與 incident decision log。"
weight: 8
tags: ["backend", "message-queue", "implementation", "replay", "incident"]
---

Queue consumer retry 與 replay handoff 的核心責任是把 request 外副作用做成可重試、可去重、可隔離、可重播的服務流程。這篇以 `order_created` consumer 為例，示範 delivery、processing、recovery 三層語意如何交接到 evidence package、release gate 與 incident decision log。

## 服務路徑與語意分層

這條路徑是 `order-service -> broker -> order-created-consumer -> invoice/email/search/webhook`。Producer 把事件交給 broker 後，真正的業務完成要看 consumer 是否正確提交副作用。

這篇先固定三層語意：

1. Delivery semantics：訊息是否投遞與確認。
2. Processing semantics：副作用是否可承受重複與部分失敗。
3. Recovery semantics：故障後是否可重播並恢復一致。

[ack/nack](/backend/knowledge-cards/ack-nack/) 成功只代表 delivery 進度，不代表發票與通知已完成。

## Event Contract 與相容邊界

Event contract 的責任是讓 producer 與 consumer 在版本演進時仍可互通，且可被觀測與回放。

`order_created` 最小欄位：

1. `event_id`：全域唯一識別。
2. `schema_version`：事件版本。
3. `occurred_at`：事件發生時間。
4. `order_id`、`tenant_id`：業務定位。
5. `idempotency_key`：副作用去重鍵。
6. `pii_scope`：敏感欄位範圍。

版本演進採向後相容優先：新增欄位可選、舊欄位保留窗口。schema 演進前要先確認 consumer 端 fallback 解析邏輯存在，避免切版後整批進 DLQ。

## Retry / DLQ / Quarantine

Retry 的責任是吸收暫時性故障，不把短暫抖動升級成事故。這條路徑使用有限重試 + backoff + jitter：

| 階段       | 判讀重點                     | 動作                                                                  |
| ---------- | ---------------------------- | --------------------------------------------------------------------- |
| 即時重試   | 下游短暫 timeout 或限流      | 在主通道重試少量次數                                                  |
| 延遲重試   | 故障持續但可恢復             | 延長 backoff，避免重試風暴                                            |
| DLQ 隔離   | payload 或版本異常、長時故障 | 轉入 [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/) |
| Quarantine | 同型 poison message 連續爆發 | 停主通道回放，先分群診斷                                              |

DLQ 的責任是隔離與診斷，不是永久儲存。重點是把異常訊息分群後對應修法，修完再定向回放。

## Idempotency 與 Ack Timing

Idempotency 的責任是把 at-least-once 交付轉成可接受業務結果。副作用如發票、email、webhook 都要以 `idempotency_key` 做去重。

Ack timing 的原則是「核心副作用提交後再 ack」：

1. 先執行副作用或落地可追蹤結果。
2. 成功後寫去重紀錄或 checkpoint。
3. 最後 ack broker。

先 ack 再副作用會造成資料遺失；副作用成功但去重紀錄失敗，則要由 recovery 層補償。

## Replay Runbook

Replay 的責任是故障後在可控範圍內恢復，不把修復變成第二次事故。

這條路徑的 replay runbook：

1. 選定 replay window：依 `occurred_at` 與 `schema_version` 分段。
2. Dry run：先在影子通道跑去重與下游容量驗證。
3. 限速回放：按 tenant 或 partition 分批，監控下游錯誤率。
4. Reconciliation：對帳發票、通知、索引結果。
5. Stop condition：duplicate side-effect、downstream timeout、DLQ 再爆發即停。

replay window 要能被明確描述與回放，不可用「重播昨天全部」這種不可驗證句子。

## Job queue 的拓樸分工

當背景工作同時要 *高吞吐* 跟 *快速反應*、單一通道模型會變成瓶頸。job queue 的擴展通常是 *拓樸重整*、把不同工作類型切到不同傳遞路徑、而非單點替換。

對應 [3.C5 Slack Job Queue 演進到 Kafka + Redis](/backend/03-message-queue/cases/slack-job-queue-kafka-redis/) — Slack 在 job queue 擴展時把工作切到不同傳遞路徑、Kafka 跟 Redis 分別承擔持久性跟即時性目標、分開治理 lag、重試跟失敗重播。

**拓樸分工的判讀**（基於 Slack case 揭露的雙通道分工方向）：

- **持久性主導的 job**（發票、付款通知、合規記錄）→ Kafka / 持久 queue、保證 at-least-once
- **即時性主導的 job**（線上提醒、playback control、UI 更新）→ Redis / 輕量 queue、low latency

設計含義：同一 consumer 應專注單一目標（高吞吐 / 即時 / 持久擇一）、其他目標拆到對應路徑。對應 [3.4 consumer-design 三個工程議題鐵三角](/backend/03-message-queue/consumer-design/) — idempotency / 重播流程 / 下游承載能力是 consumer 內部設計、拓樸分工是 *跨 consumer* 的責任拆分、兩者互補。

## Job queue 規模差異的治理重點

不同規模服務的 job queue 治理問題差異大、SSoT 在本章。對應 [3.C10 對照：規模差異下的佇列模型](/backend/03-message-queue/cases/contrast-queue-model-by-scale/)：

- **小型服務**：優先用 managed queue（SQS / Pub/Sub）、運維成本最低。最容易忽略的是語意邊界（重試次數、死信規則、重播責任）、規模一上來會出現資料重複與漏處理。**升級訊號**：team 數超 3-5 個、各自寫 consumer 開始出現 idempotency 不一致、進中型階段
- **中型服務**：常見問題是 lag 與 DLQ 長期累積。原因是 consumer idempotency + 重播流程 + 下游承載能力沒一起設計。對應前段 Job queue 拓樸分工。**升級訊號**：DLQ 累積速度高於排空速度連續 7 天、單一 tenant 流量尖峰拖垮其他 tenant、進大型階段
- **大型服務**：需要處理跨租戶跟跨區壓力。單叢集思維會讓任何一類流量尖峰拖垮整體。對應 [3.C4 LinkedIn Tiered Clusters](/backend/03-message-queue/cases/linkedin-kafka-tiered-clusters/) 跟 [3.1 broker-basics 分層治理平台](/backend/03-message-queue/broker-basics/)、重點從「怎麼送訊息」轉成「怎麼隔離失敗」

判讀重點：當前服務規模決定要處理的 *主要* 問題。規模尚小的服務硬上 multi-tenant 隔離治理屬過度設計、規模化服務應同時考慮 broker 容量是否充足跟隔離邊界是否完整。判斷自己在哪個階段、看 *升級訊號* 對應的指標。

## Evidence Package

Queue evidence 的責任是證明「投遞可達」與「處理可恢復」兩者同時成立。

| 欄位                                                   | 內容                                                           |
| ------------------------------------------------------ | -------------------------------------------------------------- |
| Source                                                 | broker metric、consumer metric、DLQ log、reconciliation query  |
| [Time range](/backend/knowledge-cards/time-range/)     | retry/replay 批次窗口                                          |
| [Query link](/backend/knowledge-cards/query-link/)     | lag、retry count、DLQ count、duplicate side-effect、throughput |
| Owner                                                  | queue owner、consumer owner、downstream owner                  |
| [Data quality](/backend/knowledge-cards/data-quality/) | 指標延遲、抽樣缺口、對帳覆蓋率                                 |
| [Confidence](/backend/knowledge-cards/confidence/)     | confirmed / suspected / needs follow-up                        |
| [Known gap](/backend/knowledge-cards/known-gap/)       | 尚未驗證之下游 webhook 供應商、低流量 tenant replay            |

這份 evidence 要對齊 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 與 [6.23 Verification Evidence Handoff](/backend/06-reliability/verification-evidence-handoff/)。

## Release Gate

Queue release gate 的責任是決定是否擴大回放或恢復主通道，而不是只看單一 lag 指標。

| Gate 欄位                                                | 最小內容                                                    |
| -------------------------------------------------------- | ----------------------------------------------------------- |
| [Gate decision](/backend/knowledge-cards/gate-decision/) | 放行下一批 replay、維持觀察、暫停 consumer                  |
| Checks                                                   | idempotency proof、DLQ drain 結果、下游容量、duplicate 比例 |
| Stop condition                                           | retry storm、DLQ 再爆發、下游錯誤率超門檻                   |
| Rollback window                                          | replay 可中止窗口、主通道可回切時間                         |
| Owner                                                    | queue on-call、business owner                               |

這組欄位對齊 [6.12 Idempotency 與 Replay 驗證](/backend/06-reliability/idempotency-replay/) 與 [6.8 Release Gate](/backend/06-reliability/release-gate/)。

## Incident Decision Log

pause consumer、drain DLQ、啟動 replay、停止 replay、執行補償都屬事故決策，需寫入 [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

```yaml
incident_decision:
  timestamp: 2026-05-11T13:18:00Z
  decision: "pause invoice consumer and start scoped replay for tenant A"
  context: "duplicate invoices increased after consumer version rollout"
  evidence:
    - query: duplicate_invoice_ratio_tenant_a
    - query: dlq_events_by_schema_version
  owner: queue-incident-commander
  expected_effect: "stop duplicate side effects and restore invoice consistency"
  rollback_condition: "duplicate ratio does not decrease within two replay batches"
```

## Case Write-back 與邊界

這篇回寫對齊 [3.C9 反例](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/)，重點是切換時語意分層混淆導致 delivery 成功但業務結果失真。

這篇不處理同步 API latency、cache TTL 或 deployment drain。若風險在同步交易壓力、快取失效或流量切換，路由到 [4.22 Checkout API Evidence Package](/backend/04-observability/checkout-api-evidence-package/)、[2.9 Cache Migration 與 Stampede Rollback](/backend/02-cache-redis/cache-migration-stampede-rollback/) 或 [5.8 Deployment Rollout with Drain and Rollback](/backend/05-deployment-platform/deployment-rollout-drain-rollback/)。
