---
title: "3.5 攻擊者視角（紅隊）：傳遞層弱點判讀"
date: 2026-04-24
description: "從重複投遞、重放濫用、毒訊息與容量壓力，盤點 message delivery 的主要弱點"
weight: 5
tags: ["backend", "message-queue"]
---

傳遞層紅隊判讀的核心目標是確認「訊息如何被重送、重放、放大與耗盡資源」。這裡的紅隊指攻擊者視角的風險檢查：先找可被放大的傳遞路徑，再回推控制面。只要系統採用 [broker](/backend/knowledge-cards/broker/) 或 stream，弱點就會同時落在 [delivery semantics](/backend/knowledge-cards/delivery-semantics/)、consumer 容量與回復流程。

## 【判讀】傳遞層弱點的主要軸線

傳遞層弱點可分成三條軸線：投遞語意、處理語意、回復語意。投遞語意看 [ack/nack](/backend/knowledge-cards/ack-nack/) 與重送條件；處理語意看 [idempotency](/backend/knowledge-cards/idempotency/) 與 side effect；回復語意看 [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/)、[replay runbook](/backend/knowledge-cards/replay-runbook/) 與 [data reconciliation](/backend/knowledge-cards/data-reconciliation/)。

## 【可觀察訊號】何時要提高紅隊檢查優先級

下列訊號出現時，傳遞層通常需要先做弱點盤點：

- [consumer lag](/backend/knowledge-cards/consumer-lag/) 持續增加，且重試量同步升高
- [DLQ](/backend/knowledge-cards/dead-letter-queue/) 累積速度高於排空速度
- 同一事件會被多路 consumer 讀取並觸發多個下游 side effect
- 回放流程缺少操作邊界與審核節點

## 【失敗代價】傳遞層弱點的代價型態

傳遞層弱點會把局部錯誤放大成系統性壓力。重複投遞會造成重複扣款、重複通知或重複建單；毒訊息會阻塞分區與 worker；重放策略缺少邊界會把歷史事件再次推進生產流程。這些問題的共同代價是資料偏移、事故窗口延長與操作風險上升。

## 【最低控制面】進入服務實體前要先定義

傳遞層在討論具體服務前，先定義四個控制面最穩定：

1. 投遞保證模型：哪些流程接受 at-least-once、哪些流程需要更嚴格保證。
2. 去重與副作用模型：哪些操作必須具備 idempotency，如何界定重複。
3. 重試與降載模型：重試節奏、上限、退避與壓力保護機制。
4. 回復與重放模型：DLQ 分流、回放準入條件與結果校正流程。

## 多租戶 broker 的隔離邊界

Multi-tenant broker 的隔離邊界承擔「單租戶故障不放大到其他租戶」的責任。Multi-tenant broker 的紅隊重點是跨租戶邊界能否擋住攻擊放大跟資源耗盡。3.1 已建立規模化分層討論、本段聚焦攻擊面跟控制面。

對應 [3.C6 Uber Kafka Infrastructure Evolution](/backend/03-message-queue/cases/uber-kafka-infrastructure-evolution/) — case 提出方向：定義租戶隔離、配額規則、標準化 topic 治理、平台指標治理。對應 [3.C4 LinkedIn Tiered Clusters](/backend/03-message-queue/cases/linkedin-kafka-tiered-clusters/) — 規模化分層 cluster、高優先 workload 跟低優先 workload 各自獨立、降低 noisy neighbor 風險。以下攻擊面 taxonomy 基於通用 multi-tenant broker 知識展開、非 case 原文列舉。

**Multi-tenant broker 的攻擊面**：

- **配額耗盡**：單一 tenant 大量 publish 占光 broker bandwidth / storage、其他 tenant 投遞延遲拉長。對應控制是 *per-tenant quota* + *rate limit*。下游推送 quota 作為硬上限見 [3.2 下游推送是隱性瓶頸](/backend/03-message-queue/durable-queue/)
- **Topic 命名衝突 / 越權**：tenant A 透過命名衝突或缺失 ACL 取得 tenant B topic 存取權限。對應控制是 *namespace 強制隔離* + *IAM topic-level ACL*
- **DLQ 跨租戶污染**：tenant A 的 poison message 進共用 DLQ、影響 tenant B 的 DLQ 處理流程。對應控制是 *per-tenant DLQ* + *獨立排空策略*
- **Consumer group 命名衝突**：意外或惡意註冊跟其他 tenant 同名的 consumer group、搶 partition 分配。對應控制是 *consumer group naming convention* + *prefix-based ACL*

判讀重點：multi-tenant broker 的紅隊不只看 broker 容量是否充足、還要看單一 tenant 出事時其他 tenant 是否受影響。單一租戶事件擴散到其他租戶屬隔離失敗、非 broker 效能問題。

## Replay 攻擊跟 DLQ 濫用

Replay 機制是事故恢復工具、也是攻擊面。攻擊者可能濫用 replay 重複觸發副作用（重複退款、重複送通知、重複下單）、或讓 DLQ 變成 backdoor 通道。以下 3 個攻擊向量基於通用紅隊知識展開、非 case 原文列舉。

**Replay 攻擊向量**：

- **未授權 replay 觸發**：攻擊者拿到 replay 控制權、replay 舊事件造成重複副作用。對應控制是 *replay 授權需獨立審核* + *audit trail 記錄誰 replay 什麼*
- **Replay window 越界**：replay 跨越 idempotency 紀錄到期、舊事件被當新事件處理。對應控制是 *replay window 上限 = idempotency 保留期*、見 [3.6 processing-recovery-semantics 的 replay 跟 idempotency 共設計](/backend/03-message-queue/processing-recovery-semantics/)
- **DLQ message 注入**：攻擊者把惡意 message 直接寫進 DLQ、繞過主通道驗證、等 replay 時觸發副作用。對應控制是 *DLQ 寫入權限獨立於主通道* + *replay 前 schema 重新驗證*

判讀重點：replay 屬 production 操作、跟 [1.9 reconciliation 修復權限管理](/backend/01-database/reconciliation-data-repair/) 同層級、要 audit trail + 審核流程。合規 replay 路徑應具備 audit trail + window 上限 + DLQ 寫入隔離三層控制、把 replay 從事故工具升級為可稽核的 production 操作。

## 【案例對照】

| 案例                                                                                                            | 紅隊視角重點                                           |
| --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| [3.C6 Uber Kafka Infrastructure](/backend/03-message-queue/cases/uber-kafka-infrastructure-evolution/)          | 治理視角、反推 multi-tenant 隔離攻擊面                 |
| [3.C4 LinkedIn Tiered Clusters](/backend/03-message-queue/cases/linkedin-kafka-tiered-clusters/)                | 治理視角、反推分層 cluster 跟 workload 隔離防護        |
| [3.C9 反例 Queue Semantics Mismatch](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/) | 切換語意誤配引發重複副作用、replay 跟 idempotency 失準 |

以上 3.C6 / 3.C4 屬治理視角案例、紅隊章節做反推使用（從控制面反推攻擊面）。

## 跨模組路由

1. 與 03 內部：規模化分層治理回 [3.1 broker-basics](/backend/03-message-queue/broker-basics/)；下游推送 quota 攻擊面跟 [3.2 durable-queue 下游推送是隱性瓶頸](/backend/03-message-queue/durable-queue/) 互補；replay 跟 idempotency 共設計回 [3.6](/backend/03-message-queue/processing-recovery-semantics/)
2. 與 01 的交接：replay / 補償權限管理回 [1.9 reconciliation 修復權限管理](/backend/01-database/reconciliation-data-repair/)
3. 與 04 的交接：紅隊偵測訊號（DLQ 速率、retry storm、duplicate）進 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)
4. 與 06 的交接：rule rollout 安全閘門進 [6.24 rule-rollout-safety-gate](/backend/06-reliability/rule-rollout-safety-gate/)
5. 與 08 的交接：事故當下決策進 [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)

## 【關聯卡片】

- [Poison Message](/backend/knowledge-cards/poison-message/)
- [Duplicate Delivery](/backend/knowledge-cards/duplicate-delivery/)
- [Retry Storm](/backend/knowledge-cards/retry-storm/)
- [Backpressure](/backend/knowledge-cards/backpressure/)
- [Runbook](/backend/knowledge-cards/runbook/)
