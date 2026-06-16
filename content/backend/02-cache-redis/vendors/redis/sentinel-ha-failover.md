---
title: "Redis Sentinel 與 failover 時序：從 master 死掉到 client 重連的每一段"
date: 2026-06-16
description: "Redis Sentinel 的 failover 不是一個瞬間動作，是 down 偵測 → quorum 確認 → 選主 → 提升 → 配置廣播 → client 重連的一條時序鏈，每一段都有自己的延遲與失敗模式。本文展開 Sentinel 的判定模型與這條時序、5 個讓 failover 卡住或丟資料的 production 踩坑，以及 Sentinel 撐不住該往 Cluster 或 managed 走的邊界"
weight: 16
tags: ["backend", "cache", "redis", "sentinel", "failover", "high-availability", "deep-article"]
---

> 本文是 [Redis](/backend/02-cache-redis/vendors/redis/) overview 的 implementation-layer deep article。Sentinel 處理的是「單 master 容量夠、但 master 不能是單點」的 HA 場景；要橫向擴容超過單機記憶體則走 [Cluster re-sharding](/backend/02-cache-redis/vendors/redis/cluster-resharding/)，兩者解的問題不同。機制以 [Redis Sentinel 官方文件](https://redis.io/docs/latest/operate/oss_and_stack/management/sentinel/) 為準、最後檢查日 2026-06-16。

## Failover 是一條時序鏈、不是一個瞬間

「master 掛了 Sentinel 會自動切換」這句話把 failover 講成一個原子動作，但真正在 production 出事時，問題永遠出在這條鏈的某一段卡住。把 failover 攤開成時序，才看得到延遲跟資料遺失藏在哪：

```text
T0   master 失去回應
     ↓ (down-after-milliseconds)
T1   單一 Sentinel 標記 master 為 SDOWN（主觀下線）
     ↓ (Sentinel 之間互問)
T2   達到 quorum 數量的 Sentinel 同意 → ODOWN（客觀下線）
     ↓ (Sentinel 之間選出 leader 來主導 failover)
T3   leader Sentinel 從 replica 中挑一個當新 master
     ↓ (SLAVEOF NO ONE + 其他 replica 改指向新 master)
T4   新 master 提升完成
     ↓ (Sentinel 廣播新 topology、更新 DNS / 通知 client)
T5   client 發現新 master、重連、恢復寫入
```

從 T0 到 T5 的總時間決定了「寫入中斷多久」。每一段都有對應的旋鈕跟失敗模式：T0→T1 由 `down-after-milliseconds` 控制（太短誤判、太長反應慢）；T1→T2 由 quorum 設定控制（太低腦裂風險、太高切不動）；T4→T5 由 client 的 topology 感知能力控制。理解 failover 就是理解這條鏈的每一段。

對把 cache 當主要 serving layer 的服務，這條鏈的長度直接是業務中斷時間。[Tinder 的配對引擎](/backend/09-performance-capacity/cases/tinder-elasticache-valkey-matching/)每次滑動讀多個 cache、cache miss 是邊緣案例——failover 期間若寫入中斷十幾秒，新寫入的 profile 互動全部 hang，sub-millisecond 的 SLA 在這幾秒徹底失守。這也是為什麼大規模服務多半走 managed multi-AZ failover（見 ElastiCache）而非自管 Sentinel。

## 核心概念：Sentinel 的判定模型

Sentinel 是獨立於 Redis 資料節點的監控進程，它的判定靠兩層共識避免單一 Sentinel 誤判。

**SDOWN（Subjectively Down，主觀下線）**：單一 Sentinel 在 `down-after-milliseconds` 內收不到 master 的有效回應（`PING`），就主觀認定它下線。這只是一個 Sentinel 的意見，不觸發 failover。

**ODOWN（Objectively Down，客觀下線）**：當標記 SDOWN 的 Sentinel 數量達到 `quorum` 設定值，master 被客觀認定下線。只有 master 的 ODOWN 才會觸發 failover（replica 的下線只標記不 failover）。

`quorum` 是「多少個 Sentinel 同意才算真的下線」，它跟「多少個 Sentinel 同意才能執行 failover」是兩個不同的數字——後者需要 Sentinel 的多數（majority），確保同時只有一個 leader 主導 failover，避免兩個 Sentinel 各自提升不同 replica 造成腦裂。

**為什麼 Sentinel 要部署奇數個且至少三個**：quorum 跟 majority 都需要足夠的 Sentinel 投票。兩個 Sentinel 無法在其中一個故障時達成 majority；三個才能容忍一個故障。Sentinel 應部署在不同故障域（不同 AZ / 機架），且不要跟 Redis 資料節點同生共死。

**Sentinel 不是 proxy**：client 不透過 Sentinel 讀寫資料。client 向 Sentinel 查詢「現在的 master 是誰」，拿到地址後直連 Redis。failover 後 client 必須重新向 Sentinel 查詢——這是 T4→T5 的關鍵，client library 要支援 Sentinel 模式才能自動完成。

## 配置：Sentinel 的設定路徑

最小三 Sentinel 配置，每個 Sentinel 一份 `sentinel.conf`：

```bash
# sentinel.conf
# 監控名為 mymaster 的 master、quorum=2（三個 Sentinel 中兩個同意算 ODOWN）
sentinel monitor mymaster 10.0.0.1 6379 2

# 多久收不到回應算 SDOWN（5 秒）
sentinel down-after-milliseconds mymaster 5000

# failover 後同時最多幾個 replica 去 resync 新 master
# 設 1 = 串行 resync、避免所有 replica 同時 resync 拖垮新 master
sentinel parallel-syncs mymaster 1

# failover 整體逾時（三分鐘內沒完成算失敗、可重試）
sentinel failover-timeout mymaster 180000
```

啟動 Sentinel：

```bash
redis-sentinel /path/to/sentinel.conf
# 或 redis-server /path/to/sentinel.conf --sentinel
```

client 端要用 Sentinel-aware 連線（以 Python redis-py 為例）：

```python
from redis.sentinel import Sentinel

sentinel = Sentinel(
    [("10.0.0.10", 26379), ("10.0.0.11", 26379), ("10.0.0.12", 26379)],
    socket_timeout=0.5,
)
# 寫入走 master（failover 後自動重新發現）
master = sentinel.master_for("mymaster", socket_timeout=0.5)
master.set("key", "value")
# 讀取可走 replica
replica = sentinel.slave_for("mymaster", socket_timeout=0.5)
replica.get("key")
```

關鍵：client 透過 `master_for` 拿到的是一個會在 failover 後重新查詢 Sentinel 的連線封裝，不是寫死的 IP。直接寫死 master IP 的 client 在 failover 後會持續連到死掉的舊 master。

### 防腦裂的兩個 master 端設定

Sentinel 選主的同時，要防止舊 master 復活後繼續接受寫入（split-brain）。在 Redis master 端設：

```bash
# 至少要有 1 個 replica 連著、且 replica lag < 10 秒、master 才接受寫入
redis-cli CONFIG SET min-replicas-to-write 1
redis-cli CONFIG SET min-replicas-max-lag 10
```

這讓被網路隔離的舊 master（連不到 replica）自動停止接受寫入，避免它在隔離期間累積的寫入在復活後跟新 master 衝突。

## Production 故障演練

### Case 1：down-after 太短、網路抖動誤觸 failover

**徵兆**：master 其實沒死，只是一次短暫的網路抖動或 GC 暫停，Sentinel 卻觸發了 failover，造成一次不必要的中斷；甚至反覆 failover（flapping）。

**根因**：`down-after-milliseconds` 設太短（例如 1000ms），master 一個短暫的 STW GC 或跨 AZ 網路抖動就超過閾值，被誤判 SDOWN→ODOWN。

**修法**：

1. `down-after-milliseconds` 設成能容忍正常抖動的值（5000-10000ms 是常見起點），用實際 RTT 與 GC pause 分布反推
2. quorum 設成多數而非 1，要求多個 Sentinel 同時看到下線，過濾單一 Sentinel 的網路問題
3. Sentinel 跟 Redis 不要跨高延遲鏈路放，網路品質直接影響誤判率
4. 監控 failover 觸發頻率，flapping 是調參訊號

### Case 2：failover 後 client 連到死掉的舊 master

**徵兆**：failover 完成、Sentinel 日誌顯示新 master 已提升，但部分 application 持續寫入失敗或寫到舊 master（資料進黑洞），`CLIENT LIST` 在新 master 上看不到這些 client。

**根因**：client 寫死了 master IP，或用的 client library 不支援 Sentinel 模式，failover 後不會重新向 Sentinel 查詢新 master。

**修法**：

1. client 一律用 Sentinel-aware 連線（`master_for` / lettuce 的 Sentinel 配置），不寫死 IP
2. 確認 client library 版本支援 Sentinel 且配置正確（連的是 Sentinel port 26379，不是 Redis 6379）
3. 對 latency-sensitive 服務，failover 後可主動 rolling restart application，清掉殘留連線
4. 設 `min-replicas-to-write` 讓被隔離的舊 master 自動停寫，即使 client 連上去也寫不進，避免資料進黑洞

### Case 3：選到 lag 大的 replica、failover 丟資料

**徵兆**：failover 後發現最近幾秒的寫入不見了，新 master 的資料比預期舊。

**根因**：Redis replication 是非同步的，replica 之間 lag 不一。Sentinel 選主會優先選 lag 小的（靠 `replica-priority` 與複製 offset），但若所有 replica 都 lag 大（master 寫入遠快於複製），無論選哪個都會丟掉未複製的寫入。Sentinel 的 failover 保證可用性，不保證零資料遺失。

**修法**：

1. 設 `min-replicas-to-write` + `min-replicas-max-lag`，lag 過大時 master 主動停寫，限制資料遺失窗口
2. 監控 replication lag（`master_repl_offset` vs replica 的 offset），lag 持續大代表複製跟不上寫入，要降寫入或擴容
3. 用 `replica-priority` 把不適合當 master 的 replica（例如做備份的、跨區的）設成 0 排除
4. 需要零資料遺失的場景，Sentinel 的非同步複製不夠，走 [MemoryDB](/backend/02-cache-redis/vendors/aws-elasticache/) 的 multi-AZ transaction log（強一致持久性）

### Case 4：腦裂——舊 master 復活後雙寫衝突

**徵兆**：網路分區期間 Sentinel 提升了新 master，分區恢復後舊 master 回來，兩個 master 各自接受過寫入，資料出現衝突或舊 master 的寫入被覆蓋遺失。

**根因**：舊 master 在分區期間被隔離（連不到 Sentinel 多數），但 client 若還連得到它且它沒設停寫保護，就繼續接受寫入。分區恢復後舊 master 被降為 replica，它在分區期間的寫入被新 master 的資料覆蓋。

**修法**：

1. `min-replicas-to-write 1` + `min-replicas-max-lag 10` 是核心防護——被隔離的舊 master 連不到 replica，自動停寫
2. Sentinel 部署在多數能存活的故障域，確保分區時多數 Sentinel 在新 master 那側
3. 接受 Redis 的 CAP 取捨：Sentinel 偏向可用性，極端分區下無法完全避免資料遺失，要強一致走別的儲存層
4. failover 後監控舊 master 復活的降級流程，確認它正確變成 replica 且 resync

### Case 5：parallel-syncs 設太大、failover 後新 master 被 resync 拖垮

**徵兆**：failover 完成的瞬間新 master 延遲暴增、甚至短暫無回應，所有 replica 同時對它發起全量同步。

**根因**：`parallel-syncs` 設成大於 1（或等於 replica 數），failover 後所有 replica 同時對新 master 做 full resync。full resync 要新 master 做 BGSAVE（fork、見 [persistence deep article](/backend/02-cache-redis/vendors/redis/persistence-fork-latency/)）並把 RDB 傳給每個 replica，多個同時進行直接打爆新 master。

**修法**：

1. `parallel-syncs` 設 1，replica 串行 resync，犧牲一點恢復速度換新 master 不被拖垮
2. 確認 master 端 `repl-backlog-size` 夠大，讓短暫斷線的 replica 走部分同步（partial resync）而非全量
3. 監控 failover 後新 master 的 CPU / 記憶體，resync 期間是脆弱窗口
4. resync 的 fork 成本跟 [記憶體 headroom](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/) 直接相關，新 master 也要留 fork 空間

## Capacity / cost 邊界

Sentinel 的容量判讀，圍繞 failover 時間與資料遺失窗口：

| 訊號                     | 健康區間               | 警戒與動作                                     |
| ------------------------ | ---------------------- | ---------------------------------------------- |
| failover 總時間（T0→T5） | 數秒到十幾秒           | 過長 → 查 down-after / parallel-syncs / client |
| failover 觸發頻率        | 罕見（真實故障才觸發） | flapping → down-after 太短、quorum 太低        |
| replication lag          | < 1 秒                 | 持續大 → 寫入超過複製能力、failover 會丟資料   |
| Sentinel 數量            | 奇數、≥ 3、跨故障域    | < 3 或同故障域 → 無法容忍 Sentinel 故障        |
| 寫入中斷可容忍時間       | 業務定義               | 不可容忍 → Sentinel 不夠、走 managed multi-AZ  |

撞牆後的路由判斷：

- **單 master 容量不夠（記憶體 / 吞吐超過單機）**：Sentinel 解 HA 不解容量。要橫向擴容走 [Redis Cluster](/backend/02-cache-redis/vendors/redis/cluster-resharding/)，它自帶 sharding 與 per-shard failover。
- **不想自己運維 Sentinel 與 failover 演練**：[ElastiCache](/backend/02-cache-redis/vendors/aws-elasticache/) 的 Multi-AZ 自動 failover 把這條時序鏈託管，failover ~30 秒到幾分鐘，省掉 Sentinel 部署與調參，代價是 managed premium。
- **需要零資料遺失的強持久性**：Sentinel 的非同步複製在 failover 時會丟未複製的寫入。要強一致走 [MemoryDB](/backend/02-cache-redis/vendors/aws-elasticache/) 的 multi-AZ transaction log。

## 整合 / 下一步

Sentinel 是 HA 的一層，但它的每一段都跟其他子系統耦合：

- **跟 [Cluster re-sharding](/backend/02-cache-redis/vendors/redis/cluster-resharding/)**：Sentinel 是「不分片的 HA」，Cluster 是「分片 + 每 shard 自帶 failover」。容量需求決定走哪條，本文是前者。
- **跟 [persistence / fork latency](/backend/02-cache-redis/vendors/redis/persistence-fork-latency/)**：failover 後的 resync 靠 BGSAVE（fork），新 master 的 fork 成本是 resync 期間的脆弱點。
- **跟 [記憶體調校](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/)**：新 master 提升後要承接全部寫入並支援 replica resync 的 fork，記憶體 headroom 不能少。
- **跟 [Meta cache consistency](/backend/02-cache-redis/cases/meta-cache-consistency-upgrade/)**：failover / replica promotion 期間的 stale read 與一致性議題，是大規模 cache 治理的核心，Sentinel 的非同步複製是 stale window 的來源之一。

## 相關連結

- 上游 vendor 頁：[Redis](/backend/02-cache-redis/vendors/redis/)
- 同 vendor deep article：[Cluster re-sharding](/backend/02-cache-redis/vendors/redis/cluster-resharding/)、[persistence 與 fork latency](/backend/02-cache-redis/vendors/redis/persistence-fork-latency/)、[記憶體與淘汰調校](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/)
- 平行 vendor：[AWS ElastiCache](/backend/02-cache-redis/vendors/aws-elasticache/)（managed multi-AZ failover）
- Methodology：[Vendor 深度技術文章寫作方法論](/posts/vendor-deep-article-methodology/)
