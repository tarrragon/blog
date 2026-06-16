---
title: "Redis 連線與 pipeline：RTT 稅、連線池與一次往返打包多命令"
date: 2026-06-16
description: "Redis 單命令通常微秒級執行，但 application 端量到的延遲是毫秒級——差距全在網路往返（RTT）。pipelining 的本質不是『批次發命令』，是把 N 次 RTT 壓成 1 次。本文展開 RTT 會計、連線池配置、pipeline 與 MULTI 的差異、5 個把連線與往返寫成延遲與正確性問題的 production 踩坑，以及連線模型撞牆的邊界"
weight: 17
tags: ["backend", "cache", "redis", "connection", "pipeline", "latency", "deep-article"]
---

> 本文是 [Redis](/backend/02-cache-redis/vendors/redis/) overview 的 implementation-layer deep article。連線與往返是 application 端量到的延遲主因，跟 server 端的[記憶體](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/)、[持久化](/backend/02-cache-redis/vendors/redis/persistence-fork-latency/)調校互補。pipeline 機制以 [Redis pipelining 官方文件](https://redis.io/docs/latest/develop/use/pipelining/) 為準、最後檢查日 2026-06-16。

## 你的延遲不在 Redis、在往返

把單一 `GET` 丟進 `redis-cli --latency`，會看到 server 端執行時間是微秒級。但 application 端的 APM 量到的 Redis 呼叫卻是 1-3ms。這個差距不是 Redis 變慢了，是網路往返（round-trip time，RTT）——命令從 application 送到 Redis、結果送回來，這趟來回就是毫秒級，而 Redis 的執行只佔其中一小部分。

這個認知翻轉了 Redis 優化的方向：當你的服務每個請求要打 10 個 Redis 命令，瓶頸不是 Redis 的吞吐，是 10 次 RTT 疊加成 10-30ms。pipelining 常被講成「批次發命令省效能」，但它真正消除的是 RTT 稅——把 10 次往返打包成 1 次往返，server 端執行時間幾乎不變，但 application 端延遲從 10×RTT 降到 1×RTT。

對每次互動要查多個 cache 的服務，這筆 RTT 稅是延遲預算的主要支出。[Snap 在 multi-cloud 架構下的痛點](/backend/09-performance-capacity/cases/snap-gcp-keydb-cross-cloud/)正是這個放大版：application 在一個 cloud、cache 在另一個，每次 lookup 多吃 5-30ms 跨 cloud RTT，「5ms × 10 cache lookup = 50ms 額外延遲」。Snap 把 KeyDB 部署到同 cloud 減少跨 cloud RTT，本質就是降低往返稅。本文處理 RTT 的會計、連線池配置與 pipeline 的正確使用。

## 核心概念：RTT 會計與三種降稅手段

Redis 一次請求的延遲拆成三段：client 序列化 + 送出、網路往返（RTT）、server 執行。多數 cache 場景下 RTT 是主導項，server 執行可忽略。降低總延遲有三種手段，對應三種「省 RTT」的方式：

**連線池消除「每次都建連線」的稅**。建立 TCP 連線（三次握手）本身就是一趟 RTT，若還有 TLS 再加幾趟。每個請求都新建連線等於每次都付建連稅。連線池讓連線重用，把建連成本攤平到接近零。

**pipelining 把 N 次 RTT 壓成 1 次**。連續送 N 個命令而不等每個的回應，一次讀回 N 個結果。這要求這 N 個命令彼此無依賴（後一個不需要前一個的結果）。

**Lua script / 多 key 命令把多操作合成 1 次往返且原子**。當命令之間有依賴（讀了再決定怎麼寫），pipeline 不適用（後面的命令送出時前面的結果還沒回來），這時用 Lua script 把邏輯放到 server 端一次執行，省 RTT 又拿到原子性。

### pipeline 跟 MULTI 是不同的東西

這兩個常被混淆，但解的問題不同：

| 維度     | pipeline                      | MULTI / EXEC（transaction）          |
| -------- | ----------------------------- | ------------------------------------ |
| 主要目的 | 省 RTT（效能）                | 原子性（多命令不被打斷）             |
| 原子性   | 無——命令間可能插入其他 client | 有——EXEC 內命令連續執行不被插入      |
| 回應時機 | 全部送完一次讀回              | EXEC 後一次回所有結果                |
| 失敗處理 | 各命令獨立成敗                | 入隊期語法錯整批拒、執行期錯不回滾   |
| 適用     | 大量無依賴命令的批次讀寫      | 需要「一組命令不被其他 client 插隊」 |

pipeline 純粹是傳輸層優化，不保證原子性——pipeline 裡的命令在 server 端仍可能跟其他 client 的命令交錯。要原子性用 MULTI/EXEC 或 Lua。兩者也可以組合（在 pipeline 裡送 MULTI...EXEC）。

注意 Redis 的 MULTI/EXEC 不是關聯式 DB 的 transaction：執行期某命令出錯（例如對 string 做 list 操作）不會回滾已執行的命令，它沒有 rollback。

## 配置：連線池與 pipeline 的設定路徑

連線池配置（以 Python redis-py 為例，多數 client library 概念一致）：

```python
import redis

pool = redis.ConnectionPool(
    host="10.0.0.1", port=6379,
    max_connections=50,          # 池上限、依並發量與 Redis maxclients 反推
    socket_timeout=0.5,          # 單命令逾時（秒）——必設、否則慢命令拖垮 caller
    socket_connect_timeout=0.5,  # 建連逾時
    health_check_interval=30,    # 定期檢查連線存活、清掉壞連線
)
r = redis.Redis(connection_pool=pool)
```

`socket_timeout` 是最常被遺漏卻最關鍵的設定——沒設逾時，一個慢命令或網路黑洞會讓 caller 無限等待，連鎖拖垮上游。

pipeline 的使用：

```python
# pipeline：N 個無依賴命令、一次往返
pipe = r.pipeline(transaction=False)  # transaction=False 純 pipeline、不包 MULTI
for uid in user_ids:                  # 假設要拿 100 個 user 的 profile
    pipe.hgetall(f"user:{uid}")
results = pipe.execute()              # 一次往返拿回 100 個結果
```

依賴型操作改用 Lua（命令間有讀後寫的依賴，pipeline 不適用）：

```python
# 原子的 check-and-set：讀目前值、符合條件才更新——一次往返且原子
lua = """
local current = redis.call('GET', KEYS[1])
if current == ARGV[1] then
  redis.call('SET', KEYS[1], ARGV[2])
  return 1
end
return 0
"""
cas = r.register_script(lua)
cas(keys=["lock:resource"], args=["old_token", "new_token"])
```

`MGET` / `MSET` / `HMGET` 等原生多 key 命令是最簡單的省 RTT 手段——能用多 key 命令就不用 pipeline，更省事且原子。

## Production 故障演練

### Case 1：每請求新建連線、延遲全是建連稅

**徵兆**：Redis 呼叫延遲偏高且不穩，`INFO stats` 的 `total_connections_received` 速率極高（接近 QPS），Redis 的 `connected_clients` 反覆上下震盪。

**根因**：application 沒用連線池，或每個請求 `redis.Redis(...)` 重新建立 client。每次請求付一趟 TCP 握手（加 TLS 更多）的 RTT，建連稅疊在每個請求上。

**修法**：

1. 用連線池並重用，client 物件在 application 生命週期內共用，不是每請求建立
2. 短生命週期環境（Lambda / serverless）把連線池放在 handler 外（容器重用時連線存活）
3. 監控 `total_connections_received` 速率，遠高於合理重連頻率代表沒重用
4. TLS 場景的建連稅更高，連線重用的收益更大

### Case 2：沒設 socket_timeout、一個慢命令拖垮整條鏈

**徵兆**：某次 Redis 短暫卡頓（fork 尖峰、網路抖動），application 端大量請求 hang 住不回，thread / connection 被耗盡，影響擴散到跟 Redis 無關的請求。

**根因**：連線沒設 `socket_timeout`。Redis 一旦慢回應或網路黑洞，caller 無限等待，佔住 thread 與連線，連鎖拖垮整個服務。

**修法**：

1. 一律設 `socket_timeout`（cache 場景通常幾百 ms 就該逾時，cache 本來就該快）
2. 逾時後 application 要有 fallback（回源或降級），不是把逾時當 fatal
3. 連線池 `max_connections` 設上限，避免無限建連把 Redis 的 `maxclients` 打滿
4. fork 尖峰是常見的慢源頭，對應 [persistence deep article](/backend/02-cache-redis/vendors/redis/persistence-fork-latency/) 的延遲尖峰治理

### Case 3：一個巨大 pipeline 把 server 跟 client 都撐爆

**徵兆**：用 pipeline 批次處理時，某次塞了幾十萬個命令進一個 pipeline，Redis 記憶體尖峰、client 端記憶體爆，甚至 OOM。

**根因**：pipeline 把所有命令的 request 跟 response 都 buffer 起來。一次塞太多，server 端要 buffer 全部 reply（計入 `used_memory`、見 [記憶體調校](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/) 的 output buffer），client 端要 hold 全部結果，雙邊記憶體尖峰。

**修法**：

1. pipeline 分批（chunk），每批幾百到幾千命令，不要一個 pipeline 塞無上限
2. 大量資料的掃描用 `SCAN` 游標分批，不要 `KEYS *` 一次撈
3. 監控 client output buffer（`CLIENT LIST` 的 `omem`），異常大代表有巨型 pipeline 或慢 consumer
4. 批次大小靠 RTT 與記憶體權衡——批次越大省越多 RTT，但記憶體尖峰越高

### Case 4：在 cluster 模式對跨 slot key 開 pipeline / transaction 失敗

**徵兆**：單機 Redis 上運作正常的 pipeline 或 MULTI，搬到 [Redis Cluster](/backend/02-cache-redis/vendors/redis/cluster-resharding/) 後報 `CROSSSLOT Keys in request don't hash to the same slot`。

**根因**：Cluster 模式下 MULTI/EXEC 與某些多 key 命令要求所有 key 在同一個 hash slot。pipeline 在 cluster 下也要按 slot 分組送到對應 node——若 client library 不自動處理跨 slot，會失敗。

**修法**：

1. 同組操作的 key 用 hash tag `{...}` 強制同 slot（例如 `user:{123}:profile`、`user:{123}:settings`）
2. 用支援 cluster pipeline 的 client library，它會自動按 slot 分組
3. 設計階段就考慮 key 的 slot 分布，避免事後重構，對應 cluster re-sharding 的 hash tag 治理
4. 跨 slot 的批次邏輯改用 application 端聚合，不依賴 server 端原子性

### Case 5：把 pipeline 當 transaction 用、出現資料競態

**徵兆**：用 pipeline 做「讀一個值、根據它決定寫什麼」的邏輯，高並發下偶發資料不一致——兩個 client 讀到同樣的舊值、各自寫入，一方覆蓋另一方。

**根因**：把 pipeline 誤當原子操作。pipeline 只是把命令打包傳輸，命令之間 server 端仍可能插入其他 client 的命令——它沒有原子性。讀後寫的依賴邏輯放 pipeline 裡，等於沒有任何併發保護。

**修法**：

1. 讀後寫的依賴邏輯用 Lua script（server 端原子執行），不用 pipeline
2. 樂觀鎖場景用 `WATCH` + MULTI/EXEC（watch 的 key 被改則 EXEC 失敗、重試）
3. 分清楚需求：要省 RTT 用 pipeline，要原子性用 Lua / MULTI，兩者目的不同
4. distributed lock 場景見 [2.5 distributed lock](/backend/02-cache-redis/distributed-lock/)，Redis 的鎖有自己的正確性陷阱

## Capacity / cost 邊界

連線與往返的容量判讀，圍繞連線數與每請求往返次數：

| 訊號                              | 健康區間                      | 警戒與動作                               |
| --------------------------------- | ----------------------------- | ---------------------------------------- |
| `connected_clients`               | 穩定、遠低於 `maxclients`     | 接近 maxclients → 池太大或洩漏、調池上限 |
| `total_connections_received` 速率 | 低（連線重用）                | 接近 QPS → 沒用連線池、每請求建連        |
| 每請求 Redis 往返次數             | 盡量合併（多 key / pipeline） | 多次獨立往返 → 用 pipeline / MGET 合併   |
| client output buffer (`omem`)     | 小                            | 大 → 巨型 pipeline 或慢 consumer         |
| Redis CPU                         | 有餘裕                        | 單執行緒 CPU 滿 → 命令太重或 QPS 超單機  |

撞牆後的路由判斷：

- **單執行緒 CPU 打滿、命令吞吐到頂**：Redis 主執行緒單線處理命令，pipeline 省 RTT 但不增加 server 端平行度。CPU 到頂走 [Cluster 分片](/backend/02-cache-redis/vendors/redis/cluster-resharding/)把命令分散到多 node。
- **想要單機多核平行處理命令**：[DragonflyDB](/backend/02-cache-redis/vendors/dragonflydb/) 的 shared-nothing 多核架構讓命令在單機就能多核平行，Redis 要靠 cluster 才能達到的吞吐它單機就能撐——高吞吐單機 workload 的替代。
- **跨 cloud / 跨 region 的 RTT 是結構性瓶頸**：[Snap 的解法](/backend/09-performance-capacity/cases/snap-gcp-keydb-cross-cloud/)是把 cache 部署到跟 application 同 cloud / 同 region，從根本消除跨區 RTT——這是架構層決策，不是 pipeline 能補的。

## 整合 / 下一步

連線與往返是 application 端延遲的主因，但它跟 server 端調校互補：

- **跟 [記憶體調校](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/)**：巨型 pipeline 的 server 端 reply buffer 計入 `used_memory`、慢 consumer 的 output buffer 是記憶體洩漏源頭。
- **跟 [persistence / fork latency](/backend/02-cache-redis/vendors/redis/persistence-fork-latency/)**：fork 尖峰是 socket_timeout 必須存在的理由之一——慢源頭不只網路。
- **跟 [Cluster re-sharding](/backend/02-cache-redis/vendors/redis/cluster-resharding/)**：cluster 模式改變 pipeline / transaction 的 key 分布規則，hash tag 治理是前提。
- **跟 [2.6 high concurrency](/backend/02-cache-redis/high-concurrency-access/)**：高並發下的連線數爆炸與熱 key 是同一組壓力的不同面向，連線池上限與 local cache 兩層都是解法。

## 相關連結

- 上游 vendor 頁：[Redis](/backend/02-cache-redis/vendors/redis/)
- 同 vendor deep article：[記憶體與淘汰調校](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/)、[persistence 與 fork latency](/backend/02-cache-redis/vendors/redis/persistence-fork-latency/)、[Sentinel 與 failover 時序](/backend/02-cache-redis/vendors/redis/sentinel-ha-failover/)、[Cluster re-sharding](/backend/02-cache-redis/vendors/redis/cluster-resharding/)
- 上游概念：[2.6 high concurrency](/backend/02-cache-redis/high-concurrency-access/)、[2.5 distributed lock](/backend/02-cache-redis/distributed-lock/)
- Methodology：[Vendor 深度技術文章寫作方法論](/posts/vendor-deep-article-methodology/)
