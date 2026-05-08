---
title: "3.2 durable queue 與重試策略"
date: 2026-04-23
description: "整理持久化佇列、DLQ 與重試流程"
weight: 2
tags: ["backend", "message-queue", "durability"]
---

持久化佇列（durable queue）的核心責任是讓非同步工作在 process、節點或網路故障後仍可被恢復處理。它讓業務動作在失敗後仍有可追蹤、可重試、可隔離的路徑。

## durable 與 ephemeral 的差異

[queue](/backend/knowledge-cards/queue/) 在語意上可分 durable 與 ephemeral。ephemeral queue 側重低延遲與短暫協調，適合可丟失任務；durable queue 側重故障後可恢復，適合正式狀態相關副作用，例如付款通知、發票產生、庫存同步與合規事件記錄。

這個選擇本質上是失敗代價選擇。若任務丟失可接受，ephemeral 可降低成本；若任務丟失會造成金流、合約或審計問題，durable 是必要基線。

## 重試策略

重試策略的責任是把暫時性故障和系統性故障分開。durable queue 常見的重試組合是：有限次重試、指數退避、[jitter](/backend/knowledge-cards/jitter/) 分散峰值、超過門檻後分流到 [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/)。

重試上限與間隔要由下游承載能力決定。重試太快會形成故障放大，重試太慢會拖長恢復時間。穩定做法是把重試策略當成服務容量控制的一部分，而不是固定平台預設值。

## DLQ 與 requeue 風險

DLQ 的責任是隔離異常訊息，避免拖垮主消費流程。DLQ 不是終點，而是診斷與修復入口。每個進入 DLQ 的訊息，都應能回答：失敗原因是 payload 錯誤、下游不可用、版本不相容，還是消費邏輯缺陷。

[requeue](/backend/knowledge-cards/requeue/) 需要明確條件。直接把異常訊息無限 requeue，通常會造成隊列震盪與延遲累積。穩定做法是先隔離、分群、修復，再批次回放。

## ordering 與吞吐取捨

durable queue 在順序與吞吐之間需要明確取捨。全域順序通常成本極高，實務上多採用分區內順序：同一 key 保持順序，不同 key 可並行。這能兼顧一致性需求與處理吞吐。

順序要求越高，恢復流程越需要明確 checkpoint 與補償策略。否則故障後的重播容易造成亂序副作用，放大修復成本。

## 判讀訊號

| 訊號                         | 判讀重點                      | 對應動作                                 |
| ---------------------------- | ----------------------------- | ---------------------------------------- |
| queue depth 持續上升         | 輸入速率高於消費能力          | 擴消費能力、調整重試節奏、分流高成本任務 |
| retry ratio 升高且成功率下降 | 故障從暫時性轉為系統性        | 降級下游、縮小重試並啟動隔離策略         |
| DLQ 量快速增加               | payload/版本/邏輯異常集中爆發 | 分群診斷、修復邏輯、定向重播             |
| requeue 循環導致延遲尖峰     | 缺少隔離邊界與停損機制        | 停止盲目 requeue、先隔離後回放           |
| 消費恢復後出現大量重複副作用 | 去重與冪等保護不足            | 補 idempotency key 與 side-effect guard  |

## 常見誤區

把 durable queue 視為「寫進去就安全」，會忽略消費與恢復責任。持久化只保證訊息可取回，不保證業務結果已正確提交。

把 DLQ 當成長期倉庫，也會讓問題持續累積。DLQ 的工程價值在於快速定位異常類型並回到修復流程。

## 案例回寫

durable queue 的重試與隔離節奏可用 [3.C9 反例](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/) 回寫。先看事件中的 backlog、retry、DLQ 變化，再回到本章判讀是重試策略失衡，還是隔離邊界不清楚。
這個案例主要支撐的是「重試隔離與停損門檻」判讀，不直接支撐 outbox 交易切分；若事件核心是資料提交與發布不一致，應轉到 3.3 與 1.3。

當重試量上升且主隊列延遲同步拉高時，先拆分重試通道並收斂 DLQ 分流條件，再把停損門檻接到 [6.24 規則推送安全閘門](/backend/06-reliability/rule-rollout-safety-gate/)。

## 跨模組路由

durable queue 是非同步可靠性的起點，不是終點。

1. 與 3.4 的交接：消費與恢復語意落在 [consumer 設計與去重](/backend/03-message-queue/consumer-design/)。
2. 與 3.3 的交接：發布一致性落在 [outbox pattern](/backend/03-message-queue/outbox-pattern/)。
3. 與 4.20 的交接：queue depth、retry、DLQ 指標進入 [Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。
4. 與 6.12 的交接：重試與重播驗證進入 [Idempotency 與 Replay 驗證](/backend/06-reliability/idempotency-replay/)。
5. 與 8.19 的交接：故障隔離與回放決策進入 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 下一步路由

要從投遞語意往消費語意延伸，接著讀 [3.4 consumer 設計與去重](/backend/03-message-queue/consumer-design/)。要看 queue 切換失敗模式，接著讀 [3.C9 反例](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/)。
