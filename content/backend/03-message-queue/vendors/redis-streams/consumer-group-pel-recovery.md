---
title: "Redis Streams consumer group 與 PEL：它給你積木、不給你 broker"
date: 2026-06-16
description: "Redis Streams 有 consumer group、PEL、XACK、XCLAIM 這些可靠消費的積木，但沒有原生 DLQ、沒有自動重投策略——可靠性責任在 application 層。死掉的 consumer 留在 PEL 的訊息不會自己重投，要別的 consumer 主動 XCLAIM。本文展開 PEL 的生命週期、實機驗證的接管流程、5 個把 Redis Streams 當成完整 broker 而踩的坑"
weight: 11
tags: ["backend", "message-queue", "redis-streams", "consumer-group", "pel", "deep-article"]
---

<!-- TODO(merge): feat/backend_03 worktree 同時在深化 03 vendor overview。本檔是 main 上新增的 deep article、未動 redis-streams/_index.md。合併後須檢查：(1) 與對方主題重複 (2) redis-streams/_index.md 是否加 deep-article 指標 (3) vendors/_index.md 覆蓋表合併。 -->

> 本文是 [Redis Streams](/backend/03-message-queue/vendors/redis-streams/) overview 的 implementation-layer deep article。選型層（Redis Streams vs Kafka / RabbitMQ）見 overview；本文只處理「決定用 Redis Streams 後，可靠消費怎麼自己搭」。命令實機驗證於 redis:7、最後檢查日 2026-06-16；機制以 [Redis Streams 官方文件](https://redis.io/docs/latest/develop/data-types/streams/) 為準。

## 它給你積木、不給你 broker

選 Redis Streams 的團隊通常已經熟 Redis、要低延遲、不想再引入一套 broker。[Bitso（加密交易所）的 Order Engine](/backend/03-message-queue/cases/redis-streams-bitso-reliable-streams/) 就是這樣：每秒數千則訊息、亞毫秒延遲、要撐 BTC 價格暴動的尖峰，評估 Kafka（latency）跟 SQS（lock-in + latency）後選了 Redis Streams——團隊本來就熟 Redis。

但他們很快發現一件事：Redis Streams 給的是**可靠消費的積木**（consumer group、PEL、XACK、XCLAIM），不是一個完整的 broker。沒有原生的 dead-letter queue，沒有「重試 N 次後自動丟到別處」的策略，沒有「consumer 死了自動把它的訊息重投給別人」的機制。Bitso 最後自建了一層 "Reliable Redis Streams" 抽象，封裝 PEL 處理 + retry + 自建 DLQ，並走 idempotent processing（接受重複勝過遺失）。這個案例揭露的核心是——**Redis Streams 是「資料結構」、不是「broker 系統」，可靠性責任落在 application 層。**

本文展開那些積木裡最關鍵也最容易誤解的一塊：consumer group 的 PEL（pending entries list），以及死掉的 consumer 怎麼被接管。

## 核心概念：PEL 的生命週期

consumer group 讓多個 consumer 競爭消費同一個 stream，每則訊息只給組內一個 consumer。可靠性的關鍵在 PEL——它記錄「已投遞但還沒被 ack」的訊息。

**訊息被 XREADGROUP 取出時進 PEL**。consumer 用 `XREADGROUP ... >` 讀新訊息，這些訊息立刻被記進該 consumer group 的 PEL，標記為「投遞給 consumer-X、還沒 ack」。PEL 是 per-group 的，記著每則 pending 訊息屬於哪個 consumer、投遞了幾次、idle 多久。

**XACK 把訊息從 PEL 移除**。consumer 處理成功後 `XACK`，訊息從 PEL 移除，這則訊息的生命週期結束。沒 XACK 的訊息永遠留在 PEL——這是 at-least-once 的基礎，也是 PEL 無限成長的風險來源。

**死掉的 consumer 的 PEL 訊息不會自動重投**。這是最關鍵也最違反直覺的一點。如果 consumer-A 讀了訊息、還沒 ack 就 crash，那些訊息**留在 PEL、屬於 consumer-A、不會自動投給別人**。Redis 不會偵測 consumer 死亡、不會自動重投。必須由另一個 consumer 主動 `XCLAIM` / `XAUTOCLAIM` 把這些 idle 太久的訊息「認領」過來。這就是「給你積木、不給你 broker」的具體體現——重投是你要自己驅動的。

**XCLAIM / XAUTOCLAIM 是接管機制**。`XAUTOCLAIM` 掃描 PEL 裡 idle 超過閾值的訊息，轉移所有權給呼叫的 consumer，讓它重新處理。沒有這個主動接管，死 consumer 的訊息就永遠卡在 PEL。

## 配置：consumer group + PEL + 接管（實機驗證）

```bash
# XADD 訊息、建 consumer group（從 0 開始讀）
redis-cli XADD orders '*' id 1
redis-cli XADD orders '*' id 2
redis-cli XGROUP CREATE orders workers 0      # OK

# consumer-A 讀 2 則（用 '>' 讀新訊息）→ 進 PEL（未 ack）
redis-cli XREADGROUP GROUP workers consumer-A COUNT 2 STREAMS orders '>'

# XPENDING：看 PEL，2 則 pending、都屬 consumer-A
redis-cli XPENDING orders workers
#   2  <first-id>  <last-id>  consumer-A 2   ← PEL 有 2 則、consumer-A 持有

# 處理成功 → XACK，從 PEL 移除
redis-cli XACK orders workers <first-id>      # 1（移除 1 則）
redis-cli XPENDING orders workers             # 剩 1 則

# consumer-A 死了：consumer-B 用 XAUTOCLAIM 接管 idle 訊息（min-idle 0 = 全認領）
redis-cli XAUTOCLAIM orders workers consumer-B 0 0
#   回傳被 consumer-B 認領的訊息、重新處理
```

實機驗證於 redis:7（最後檢查日 2026-06-16）：XREADGROUP 讀的訊息進 PEL（XPENDING 可見、屬 consumer-A）、XACK 後移除、XAUTOCLAIM 讓 consumer-B 接管 consumer-A 滯留的訊息。

判讀：

- 正常流程：XREADGROUP `>` 讀新 → 處理 → XACK
- 恢復流程：定期跑 XAUTOCLAIM 掃 idle 太久的 PEL 訊息、接管重處理（這是「自建重投」）
- consumer 重啟後想重處理自己未 ack 的：XREADGROUP 用 `0`（而非 `>`）讀自己 PEL 裡的舊訊息

## Production 故障演練

### Case 1：consumer crash、訊息永遠卡在 PEL

**徵兆**：某個 consumer 掛掉後，它讀過但沒 ack 的訊息再也沒被處理，XPENDING 顯示一批 idle 很久、屬於已不存在的 consumer 的訊息。

**根因**：Redis Streams 不偵測 consumer 死亡、不自動重投。死 consumer 的 PEL 訊息就停在那裡，等人來認領——但如果沒有任何 XCLAIM / XAUTOCLAIM 流程，永遠沒人認領。

**修法**：

1. 一定要有 XAUTOCLAIM 恢復流程：定期掃 PEL 裡 idle 超過閾值的訊息、接管重處理
2. idle 閾值設成大於正常處理時間（避免把還在處理的當死的搶走）
3. 沒有恢復流程的 Redis Streams 不是可靠隊列——這是 application 層的責任
4. 對應 [Bitso 的 Reliable Streams 抽象](/backend/03-message-queue/cases/redis-streams-bitso-reliable-streams/)：把 readPending + claim 封裝成 library

### Case 2：以為有原生 DLQ、毒訊息無限重投

**徵兆**：某則訊息每次被 XAUTOCLAIM 認領、處理又失敗、再回 PEL、再被認領……無限循環，delivery count 累積到很大。

**根因**：Redis Streams 沒有原生 DLQ，也沒有「重試 N 次後自動丟棄」。XAUTOCLAIM 會一直把失敗訊息重新認領，除非 application 自己檢查投遞次數、達上限後路由到自建 DLQ。

**修法**：

1. 讀 XPENDING 的 delivery count，超過上限就把訊息 XADD 到自建的 DLQ stream、再 XACK 原訊息
2. DLQ 是另一個 stream（Redis Streams 沒有 DLQ 物件，DLQ 就是「另一條 stream」）
3. 自建 DLQ 要有處理 / 告警流程，不是 XADD 進去就沒事
4. 這正是 Bitso「N 次 retry 後路由」的做法——可靠性在 application 層

### Case 3：PEL 無限成長、吃光記憶體

**徵兆**：Redis 記憶體持續上升，XLEN 沒漲多少但 XPENDING 的數字越來越大。

**根因**：大量訊息被讀取（進 PEL）但從未 XACK——consumer 處理慢、或 ack 漏了、或死 consumer 的訊息沒被接管。PEL 是 Redis 記憶體裡的結構，無限成長會吃光記憶體（Redis Streams 繼承 [Redis 的記憶體模型](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/)）。

**修法**：

1. 確保每則訊息最終都被 XACK（成功）或路由到 DLQ + XACK（失敗），不留在 PEL
2. 監控 XPENDING 總數，持續成長代表 ack 流程有漏
3. 死 consumer 的 PEL 要被 XAUTOCLAIM 清理，不要讓 orphan 訊息累積
4. PEL 成長是 Redis 記憶體壓力的來源之一，跟 stream 本身的 MAXLEN 分開治理

### Case 4：MAXLEN trim 把還沒 ack 的訊息刪掉

**徵兆**：用 MAXLEN 限制 stream 長度後，發現有些訊息還在 PEL（未處理完）卻已經從 stream 被 trim 掉、XCLAIM 認領後讀不到內容。

**根因**：`XADD ... MAXLEN` / `XTRIM` 按 stream 長度裁剪，它不管訊息有沒有被所有 consumer group ack。trim 掉的訊息即使還在某個 PEL 裡，內容也沒了（PEL 只存 ID，內容在 stream 本體）。

**修法**：

1. MAXLEN 設足夠大，確保訊息在被所有 consumer 處理完之前不會被 trim
2. 高可靠場景用 XACK-aware 的裁剪邏輯（自己判斷最小未 ack ID 再 trim），不要無腦 MAXLEN
3. 理解 stream 長度治理跟 PEL 治理是兩件事——trim 看長度、PEL 看 ack
4. 容量規劃要把「處理延遲期間 stream 不能被 trim」算進保留長度

### Case 5：把 at-least-once 當 exactly-once、重複副作用

**徵兆**：同一筆業務操作被執行兩次（重複扣款、重複發信），尤其在 XAUTOCLAIM 接管後。

**根因**：Redis Streams 的 consumer group 是 at-least-once——XCLAIM 接管會讓訊息被重新處理，crash 後重讀自己的 PEL 也會重處理。沒有冪等保護就會重複副作用。

**修法**：

1. 消費端冪等：用業務唯一鍵去重（處理前檢查是否已處理過）
2. Bitso 明確選擇「idempotent processing 接受重複勝過遺失」——這是 at-least-once 的標準配套
3. 副作用走冪等的下游（upsert、條件寫入），不是盲目執行
4. 對應 [6.12 idempotency / replay](/backend/06-reliability/idempotency-replay/) 的冪等設計

## Capacity / cost 邊界

Redis Streams 可靠消費的容量判讀：

| 訊號                  | 健康區間                 | 警戒與動作                                     |
| --------------------- | ------------------------ | ---------------------------------------------- |
| XPENDING 總數         | 低且穩定                 | 持續成長 → ack 漏 / 死 consumer 未接管、PEL 爆 |
| PEL 訊息 idle 時間    | 短（正常處理週期內）     | 長 → consumer 死掉、需 XAUTOCLAIM 接管         |
| delivery count 分布   | 多數低（一次成功）       | 高 → 毒訊息、需自建 DLQ 路由                   |
| Redis 記憶體          | 在 maxmemory headroom 內 | PEL + stream 成長吃記憶體、見 02 記憶體調校    |
| stream MAXLEN vs 處理 | trim 不早於全 group ack  | trim 太早 → 未 ack 訊息內容遺失                |

撞牆後的路由判斷：

- **要原生 DLQ / 重投策略 / consumer 死亡偵測**：Redis Streams 都要自建；要開箱即用走 [RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/)（DLX + 自動重投）。
- **超大吞吐 + 長期保留 + 多 consumer 各自 replay**：Redis Streams 受 Redis 記憶體限制，大規模事件流走 [Kafka](/backend/03-message-queue/vendors/kafka/)（log-based、磁碟保留）。
- **記憶體 / 持久化是瓶頸**：Redis Streams 繼承 Redis 的記憶體與 [fork 持久化](/backend/02-cache-redis/vendors/redis/persistence-fork-latency/)限制，大量積壓有風險。
- **不想自建可靠性層**：Bitso 自建了 Reliable Streams library 才好用；沒有這個投入意願就選有原生可靠性的 broker。

## 整合 / 下一步

Redis Streams 的可靠消費是「自己搭 broker」，它跟 Redis 本身與其他 broker 交織：

- **跟 [02 Redis 記憶體調校](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/)**：PEL + stream 都在 Redis 記憶體，eviction / maxmemory 治理直接影響可靠性。
- **跟 [3.4 consumer design](/backend/03-message-queue/consumer-design/)**：consumer group + PEL + XCLAIM 是 consumer 設計的具體機制。
- **跟 [6.12 idempotency / replay](/backend/06-reliability/idempotency-replay/)**：at-least-once + XCLAIM 重投要求消費冪等。
- **跟 [RabbitMQ DLQ deep article](/backend/03-message-queue/vendors/rabbitmq/dlq-retry-escalation/)**：RabbitMQ 的 DLX 是原生的，Redis Streams 的 DLQ 要自建成「另一條 stream」——對照看「broker 內建 vs application 自建」的責任差異。

## 相關連結

- 上游 vendor 頁：[Redis Streams](/backend/03-message-queue/vendors/redis-streams/)
- 對照 vendor：[RabbitMQ DLQ 與分層 retry](/backend/03-message-queue/vendors/rabbitmq/dlq-retry-escalation/)、[NATS JetStream](/backend/03-message-queue/vendors/nats/jetstream-durability-consumer/)
- 對應案例：[3.C42 Bitso Reliable Redis Streams](/backend/03-message-queue/cases/redis-streams-bitso-reliable-streams/)
- 上游概念：[3.4 consumer design](/backend/03-message-queue/consumer-design/)、[02 Redis 記憶體調校](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/)
