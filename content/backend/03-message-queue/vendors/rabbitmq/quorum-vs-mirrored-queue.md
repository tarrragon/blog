---
title: "RabbitMQ quorum queue 取代 mirrored queue：可靠性不是免費的"
date: 2026-06-16
description: "Classic mirrored queue 看起來是『打開就有 HA』的免費升級，但它的 mirroring 把每則訊息同步到所有 mirror、網路成本被嚴重低估、規模化時壓垮 broker。RabbitMQ 已棄用 mirrored queue、改推 Raft-based quorum queue。本文展開兩者的複製模型差異、實機驗證 queue type、mirrored → quorum 的遷移、5 個踩坑與選型邊界"
weight: 12
tags: ["backend", "message-queue", "rabbitmq", "quorum-queue", "high-availability", "deep-article"]
---

<!-- TODO(merge): feat/backend_03 worktree 同時在深化 03 vendor overview。本檔是 main 上新增的 deep article、未動 rabbitmq/_index.md。合併後須檢查：(1) 與對方主題重複 (2) rabbitmq/_index.md 是否加 deep-article 指標 (3) vendors/_index.md 覆蓋表合併。 -->

> 本文是 [RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/) overview 的 implementation-layer deep article。選型層（RabbitMQ vs 其他 broker）見 overview；本文只處理「決定用 RabbitMQ 後，HA 隊列怎麼選」。queue type 實機驗證於 rabbitmq:3-management、最後檢查日 2026-06-16；機制以 [RabbitMQ quorum queues 官方文件](https://www.rabbitmq.com/docs/quorum-queues) 為準。

## 「打開鏡像就有 HA」是被低估成本的錯覺

Classic mirrored queue（鏡像隊列）的賣點聽起來無懈可擊：設一個 policy，隊列就自動鏡像到多個節點，主節點掛了 mirror 接手，HA 免費到手。很多團隊就這樣打開了全隊列鏡像，以為買到了可靠性。

代價藏在「同步」兩個字裡。mirrored queue 把每一則訊息、每一個 ack、每一次狀態變更都同步到所有 mirror——隊列越多、mirror 越多、吞吐越高，這個同步流量隨之放大。[Runtastic 在 2020 lockdown 流量暴增時](/backend/03-message-queue/cases/rabbitmq-runtastic-mirrored-queue-bottleneck/)踩到了這個：壓力測試揭露 mirroring 邏輯把網路元件壓垮，造成高延遲與服務中斷，調整 mirroring 配置才消除瓶頸。這個案例的教訓是——**mirrored queue 不是免費的可靠性升級，它的網路成本要被量化**，而且這正是 RabbitMQ 後來棄用 mirrored queue、改推 quorum queue 的典型動機。

quorum queue 用 Raft 共識協定重新實作了複製，把「可靠性」建立在一個有明確一致性模型、可預測複製成本的基礎上。本文展開兩者的複製模型差異、遷移路徑與選型邊界。

## 核心概念：兩種複製模型的本質差異

mirrored queue 跟 quorum queue 都做「多副本」，但複製的語意完全不同。

**mirrored queue 是 primary + mirror 的全量同步**。一個 master 隊列加 N 個 mirror，master 把所有操作同步給每個 mirror。它沒有共識協定——master 掛了由其中一個 mirror 晉升，但晉升時可能丟失 master 已接受、還沒同步完的訊息（取決於 mirror 同步進度）。同步是「盡力」的全量複製，網路成本隨 mirror 數線性疊加。

**quorum queue 是 Raft-based 的多數共識**。一個 leader 加多個 follower 組成 Raft group，一則訊息要被**多數成員確認**才算 committed。leader 掛了，Raft 選舉產生新 leader，已 committed 的訊息保證不丟（多數已持有）。複製是有共識協定保證的，一致性模型明確（committed = 多數持久化）。

**quorum queue 永遠持久、且只在多數存活時可寫**。它是 CP 傾向——多數節點存活才接受寫入（保證一致），少數分區那側拒寫。這跟 mirrored queue 的「盡力 AP」取捨不同：quorum 用「分區時少數側不可寫」換到「committed 訊息不丟」。

實機看得到 queue type 的差異：

```bash
# 宣告 quorum queue（x-queue-type=quorum）與 classic queue
rabbitmqadmin declare queue name=q.quorum arguments='{"x-queue-type":"quorum"}'
rabbitmqadmin declare queue name=q.classic

rabbitmqctl list_queues name type durable
# q.quorum    quorum    true    ← 永遠 durable、Raft 複製
# q.classic   classic   true

# quorum queue 的 Raft 成員
rabbitmqctl list_queues name type members
# q.quorum    quorum    [rabbit@node-a, rabbit@node-b, rabbit@node-c]
```

實機驗證於 rabbitmq:3-management（最後檢查日 2026-06-16）：quorum queue 回報 `type=quorum`、永遠 `durable=true`、`members` 列出 Raft group 成員（單節點時只有自己）。

## 配置：mirrored → quorum 的遷移

關鍵限制：**queue type 不能就地轉換**。mirrored（classic）queue 跟 quorum queue 是不同 type，沒有 in-place 升級——必須建新的 quorum queue、把流量切過去、排空舊隊列。

```bash
# 1. 建 quorum queue（注意：quorum 永遠 durable、不需也不能設成 transient）
rabbitmqadmin declare queue name=orders.v2 arguments='{"x-queue-type":"quorum"}'

# 2. 把 binding 複製到新隊列（與舊隊列同 exchange / routing key）
rabbitmqadmin declare binding source=orders.ex destination=orders.v2 routing_key=orders

# 3. 切換：先讓 consumer 同時消費新舊隊列、producer 改投新隊列
#    舊隊列停止進新訊息、consumer 把舊隊列排空後解綁移除

# 4. 移除舊 mirrored queue 的 HA policy 與隊列
rabbitmqctl clear_policy ha-all
rabbitmqadmin delete queue name=orders   # 確認已排空
```

quorum queue 的關鍵調校參數：

```bash
# 每隊列保留在記憶體的訊息數上限（quorum queue 預設把訊息寫盤、不全留記憶體）
#   x-max-in-memory-length / x-max-in-memory-bytes
# 投遞失敗重試上限（quorum 原生支援、避免毒訊息無限重投）
#   x-delivery-limit（達上限自動 dead-letter、配合 DLX）
rabbitmqadmin declare queue name=orders.v2 \
  arguments='{"x-queue-type":"quorum","x-delivery-limit":5,"x-dead-letter-exchange":"dlx"}'
```

`x-delivery-limit` 是 quorum queue 相對 classic 的一個實用優勢——原生的投遞次數上限，達標自動 dead-letter，不必像 classic queue 那樣靠 `x-death` count 手動判斷（見 [DLQ 與分層 retry deep article](/backend/03-message-queue/vendors/rabbitmq/dlq-retry-escalation/)）。

## Production 故障演練

### Case 1：全隊列鏡像、mirroring 流量壓垮網路

**徵兆**：流量上升時延遲暴增、broker 間網路飽和、吞吐反而下降。隊列數 × mirror 數很大。

**根因**：對所有隊列設了 `ha-mode: all` 的鏡像 policy，每則訊息同步到所有節點的所有 mirror，同步流量隨隊列數與 mirror 數放大，網路成為瓶頸——正是 [Runtastic 案例](/backend/03-message-queue/cases/rabbitmq-runtastic-mirrored-queue-bottleneck/) 的情形。

**修法**：

1. 不要無差別全隊列鏡像；只對真正需要 HA 的隊列設複製
2. 遷到 quorum queue——Raft 的複製成本可預測（多數確認、不是全量盡力同步）
3. 量化複製的網路成本（用 RabbitMQ Prometheus 監控節點間流量），不要假設鏡像免費
4. quorum queue 數量也有成本（每個是一個 Raft group），不是「越多越好」，見 Case 4

### Case 2：以為 mirrored queue failover 不丟訊息

**徵兆**：master 節點故障 failover 後，發現少了一批訊息——producer 以為發成功了。

**根因**：mirrored queue 沒有共識協定，master 接受訊息後同步給 mirror 是非同步的。master 在同步完成前掛掉，晉升的 mirror 沒有那批訊息，它們就丟了。「有 mirror」不等於「不丟訊息」。

**修法**：

1. 需要「committed 不丟」走 quorum queue（Raft 多數確認才算 committed）
2. mirrored queue 即使用 publisher confirm 也只保證到 master、不保證所有 mirror
3. quorum queue + publisher confirm 才是「確認 = 多數持久化」的可靠語意
4. 評估資料重要性：可重建的訊息容忍 mirrored 的盡力複製，不可重建的走 quorum

### Case 3：quorum queue 在少數節點存活時拒寫

**徵兆**：3 節點 cluster 掛了 2 個，剩 1 個節點上的 quorum queue 無法寫入、producer 報錯。

**根因**：quorum queue 是 CP——要多數成員（3 節點中至少 2 個）存活才接受寫入。只剩 1 個是少數，為了保證一致性而拒寫。這是設計，不是 bug。

**修法**：

1. 理解 quorum 的取捨：少數分區拒寫換來不丟已 committed 訊息（CP 而非 AP）
2. cluster 規模給足（3 或 5 節點），容忍 1 或 2 節點故障仍有多數
3. 不能容忍「分區時拒寫」的場景，重新評估是否該用 quorum（或該換 broker 模型）
4. 監控 quorum group 的成員健康，及早發現節點掉出多數

### Case 4：大量 quorum queue 吃光記憶體 / 檔案描述符

**徵兆**：建了上萬個 quorum queue 後 broker 記憶體與 fd 吃緊、效能下降。

**根因**：每個 quorum queue 是一個獨立的 Raft group（有自己的 log、成員、選舉），固定開銷比 classic queue 高。海量小隊列場景下，quorum 的 per-queue 開銷會累積成問題。

**修法**：

1. quorum queue 適合「數量可控、需要強可靠性」的隊列，不適合海量臨時小隊列
2. 海量短生命週期隊列用 classic queue（無 Raft 開銷）
3. 設計上減少隊列數（共用隊列 + routing key 區分），不要 per-entity 一個 quorum queue
4. 監控隊列總數與 broker 資源，quorum queue 數量是容量規劃的一個維度

### Case 5：遷移時想就地把 classic 轉 quorum、失敗

**徵兆**：嘗試把現有 classic queue 改成 quorum、或對 quorum queue 設 mirrored policy，操作報錯或無效。

**根因**：queue type 是宣告時固定的、不能就地轉換；mirrored 是 classic queue 的 policy、不適用 quorum queue。兩者是不同的隊列實作。

**修法**：

1. 遷移必須建新 quorum queue + 切流量 + 排空舊隊列（見配置段），沒有 in-place 升級
2. quorum queue 不需要也不接受 mirrored policy（它自帶 Raft 複製）
3. 切換期讓 consumer 同時消費新舊隊列，平滑過渡
4. 規劃 cutover 視窗，舊隊列確認排空再刪除

## Capacity / cost 邊界

quorum vs mirrored 的容量判讀：

| 維度                | classic mirrored queue     | quorum queue              |
| ------------------- | -------------------------- | ------------------------- |
| 複製模型            | 全量盡力同步（無共識）     | Raft 多數共識             |
| failover 訊息保證   | 可能丟未同步完的訊息       | committed（多數持久）不丟 |
| 一致性傾向          | AP 盡力                    | CP（少數分區拒寫）        |
| 複製網路成本        | 隨 mirror 數線性、易被低估 | 可預測（多數確認）        |
| per-queue 開銷      | 低                         | 高（每個是 Raft group）   |
| 持久性              | 可 transient               | 永遠 durable              |
| 原生 delivery-limit | 無（靠 x-death 手動）      | 有（x-delivery-limit）    |
| 官方狀態            | 已棄用（4.0 移除）         | 推薦的 HA 隊列            |

撞牆後的路由判斷：

- **海量小隊列 / 短生命週期**：quorum 的 per-queue 開銷太高，用 classic queue（不鏡像或精選鏡像）。
- **需要極高吞吐 + 長期保留 + replay**：RabbitMQ 的隊列模型本質是「消費即刪」，大規模 replay 走 [Kafka](/backend/03-message-queue/vendors/kafka/)（log-based、consumer 各自 offset）。
- **不想自管 HA / cluster**：managed 的 [AWS SQS](/backend/03-message-queue/vendors/aws-sqs/)（內建冗餘、無隊列 HA 配置負擔）或 managed RabbitMQ。
- **分區時必須可寫（AP）**：quorum 的 CP 取捨不適合，重新評估隊列模型或 broker 選型。

## 整合 / 下一步

quorum queue 是 RabbitMQ HA 的現行答案，它跟其他議題交織：

- **跟 [DLQ 與分層 retry](/backend/03-message-queue/vendors/rabbitmq/dlq-retry-escalation/)**：quorum queue 的 `x-delivery-limit` 原生支援投遞上限自動 dead-letter，簡化 retry 拓樸；DLQ 本身也該用 quorum 確保死信持久。
- **跟 [3.1 broker basics](/backend/03-message-queue/broker-basics/)**：複製與一致性模型是 broker 可靠性的根基，quorum 的 Raft 是具體實現。
- **跟 [3.2 durable queue](/backend/03-message-queue/durable-queue/)**：quorum queue 永遠 durable，是 durable queue 的預設選擇。
- **跟 [6.x reliability](/backend/06-reliability/)**：quorum 的 CP 取捨（分區拒寫）是 reliability budget 的一部分，要跟可用性目標一起權衡。

## 相關連結

- 上游 vendor 頁：[RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/)
- 同 vendor deep article：[DLQ 與分層 retry escalation](/backend/03-message-queue/vendors/rabbitmq/dlq-retry-escalation/)
- 對應案例：[3.C30 Runtastic mirrored queue 網路瓶頸](/backend/03-message-queue/cases/rabbitmq-runtastic-mirrored-queue-bottleneck/)
- 上游概念：[3.1 broker basics](/backend/03-message-queue/broker-basics/)、[3.2 durable queue](/backend/03-message-queue/durable-queue/)
