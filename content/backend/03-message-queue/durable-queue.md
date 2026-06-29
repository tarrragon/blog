---
title: "3.2 durable queue 與重試策略"
date: 2026-04-23
description: "整理持久化佇列、DLQ 與重試流程"
weight: 2
tags: ["backend", "message-queue", "durability"]
---

持久化佇列（[durable queue](/backend/knowledge-cards/durable-queue/)）的核心責任是讓非同步工作在 process、節點或網路故障後仍可被恢復處理。它讓業務動作在失敗後仍有可追蹤、可重試、可隔離的路徑。

## durable 與 ephemeral 的差異

[queue](/backend/knowledge-cards/queue/) 在語意上可分 durable 與 ephemeral。ephemeral queue 側重低延遲與短暫協調，適合可丟失任務；durable queue 側重故障後可恢復，適合正式狀態相關副作用，例如付款通知、發票產生、庫存同步與合規事件記錄。

這個選擇本質上是失敗代價選擇。若任務丟失可接受，ephemeral 可降低成本；若任務丟失會造成金流、合約或審計問題，durable 是必要基線。

## 重試策略

重試策略的責任是把暫時性故障和系統性故障分開。durable queue 常見的重試組合是：有限次重試、指數退避、[jitter](/backend/knowledge-cards/jitter/) 分散峰值、超過門檻後分流到 [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/)。

重試上限與間隔要由下游承載能力決定。重試太快會形成故障放大，重試太慢會拖長恢復時間。穩定做法是把重試策略當成服務容量控制的一部分，而不是固定平台預設值。

## DLQ 與 requeue 風險

DLQ 的責任是隔離異常訊息，避免拖垮主消費流程。DLQ 是診斷與修復入口，把它當終點會讓問題沉積。每個進入 DLQ 的訊息，都應能回答：失敗原因是 payload 錯誤、下游不可用、版本不相容，還是消費邏輯缺陷。

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

## 訊息系統的「通知 vs 訊息」分類

訊息系統設計區分兩種 SLO 不同的傳遞責任：*transactional 通知* 承擔業務副作用的可靠送達、*broadcast 訊息* 承擔大量低成本傳播。兩者用不同 storage、不同重試策略、不同投遞保證。

對應 [9.C26 PayPay](/backend/09-performance-capacity/cases/paypay-mobile-payment-messaging/) — 行動支付每日 3 億訊息、付款通知承擔「確認交易完成」的業務責任、SLO 包含秒級延遲跟高投遞率（用戶付完款後若 30 秒沒收到通知會打客服、產生重複扣款風險）。這層需求嚴於 OTA 推播、需要 durable queue + retry + 重複偵測。

**分類設計**：

- **Transactional 通知**（付款收據、訂單狀態變更、配額警告）：承擔業務副作用確認、需 durable + idempotency key 去重、SLO 通常是 *秒級延遲 + 99.99% 投遞率*
- **Broadcast 訊息**（行銷推播、新片發布通知、社群動態）：承擔大量低成本傳播、SLO 是 *吞吐量* 跟覆蓋率、允許 best-effort retry

判讀含義：規模化訊息系統的容量規劃要按類別分開、避免套同一個 broker capacity。3 億訊息 / 天看似一致、但 *通知* 跟 *訊息* 的工程負擔差數量級。

## 下游推送是隱性瓶頸

訊息系統的真正瓶頸常落在 *下游推送通道*（APNs、FCM、SMS gateway、email provider）、不在 broker。下游 quota 是 hard ceiling、超過會被 throttle、訊息積壓回 broker 形成 backlog。

對應 [9.C26 PayPay](/backend/09-performance-capacity/cases/paypay-mobile-payment-messaging/) — DynamoDB 寫入可以撐 3K msg/sec 平均（PayPay 本身用 DynamoDB 作訊息後端、不是傳統 broker）、但 APNs 推送額度成為事故當下的隱性瓶頸。容量規劃要把下游 quota 算進去、不只看訊息後端吞吐。

**設計含義**：

- **下游 quota 視為容量上限**：APNs / FCM / SMS 的 daily quota 是 hard ceiling、訊息後端規劃要對應
- **下游通道多元化**：用 APNs / FCM / SMS / in-app notification 多通道分攤 quota 壓力、單通道飽和時其他通道仍可送出（具體降級策略需依各組織業務規則設計）
- **重試節奏跟下游容量對齊**：consumer 重試節奏依下游剩餘 quota 動態調整、讓重試節奏跟容量同步

判讀重點：訊息系統事故當下、先看下游推送通道狀態（APNs status、FCM error rate）、再看訊息後端。下游 throttle 引發 backlog 是規模化訊息系統最常見的瓶頸來源。下游推送 quota 的攻擊面對照見 [3.5 multi-tenant broker 配額耗盡](/backend/03-message-queue/red-team-delivery-layer/)。

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
