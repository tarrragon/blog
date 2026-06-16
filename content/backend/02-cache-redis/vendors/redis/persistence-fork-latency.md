---
title: "Redis 持久化與 fork latency：AOF、RDB 與那一次卡住整個 cluster 的 fork"
date: 2026-06-16
description: "Redis 的 RDB save 與 AOF rewrite 都靠一次 fork()，而 fork 在大記憶體實例上會凍結主執行緒數百毫秒、複製分頁讓記憶體逼近翻倍。本文展開 AOF / RDB 的機制與 fsync 取捨、copy-on-write 的記憶體放大、5 個把持久化寫成延遲尖峰與資料遺失的 production 踩坑，以及 cache 場景到底要不要持久化的邊界"
weight: 15
tags: ["backend", "cache", "redis", "persistence", "aof", "rdb", "deep-article"]
---

> 本文是 [Redis](/backend/02-cache-redis/vendors/redis/) overview 的 implementation-layer deep article。持久化跟[記憶體調校](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/)互相耦合（fork 的 copy-on-write 是 maxmemory headroom 的主要消耗者），兩篇建議一起讀。機制以 [Redis persistence 官方文件](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/) 為準、最後檢查日 2026-06-16。

## fork 那一瞬間

Redis 是單執行緒處理命令的，這是它延遲可預測的根基——直到它需要把記憶體裡的資料寫到磁碟。RDB snapshot 跟 AOF rewrite 都不能在主執行緒上慢慢做（會凍結所有命令），於是 Redis 的解法是 `fork()`：複製出一個子進程，由子進程把當下的記憶體快照寫到磁碟，主進程繼續服務。

問題在 `fork()` 本身不是免費的。Linux 的 `fork()` 要複製父進程的分頁表（page table），記憶體越大、分頁表越大，這個複製動作越久——而它發生在主執行緒上，是阻塞的。一個 20GB 的 Redis 實例，fork 可能凍結主執行緒數百毫秒到一秒。在這段時間裡，所有命令排隊，p99 延遲從 1ms 跳到 500ms+。

更糟的是 fork 之後。`fork()` 用 copy-on-write：子進程跟父進程共享實體分頁，直到某一方寫入才複製。子進程只讀（在寫 snapshot），但父進程持續服務寫入，每改一個分頁就觸發一次複製。寫入越密集、snapshot 跑越久，被複製的分頁越多，最壞情況記憶體接近翻倍。這就是為什麼 Redis 的 maxmemory 必須留 headroom——不是給資料，是給 fork 期間的分頁複製。

理解持久化，本質是理解「fork 的延遲尖峰」與「資料持久性」之間的取捨。本文按這條線展開機制、配置與踩坑。

## 核心概念：AOF 與 RDB 是兩種不同的持久性語意

Redis 的兩種持久化不是「二選一的同類選項」，它們回答的是不同問題。

**RDB 是某個時間點的記憶體快照**。它把整個 dataset 序列化成一個緊湊的二進位檔（`dump.rdb`）。優點是檔案小、還原快（直接載入記憶體）、fork 一次寫完。缺點是兩次 snapshot 之間的寫入會在崩潰時全部遺失——RDB 的持久性顆粒度是「上一次 save 到現在」，可能是幾分鐘的資料。

**AOF 是命令的 append-only log**。每個改變資料的命令（`SET`、`LPUSH`...）被追加到 log 檔，還原時重放整個 log。優點是持久性顆粒度細（最多丟 `fsync` 策略決定的一小段）。缺點是 log 會無限增長，需要定期 rewrite 壓縮——而 rewrite 也要 fork。

兩者的 fork 觸發點不同但機制相同：RDB 是 `BGSAVE`（手動或 save 規則觸發）fork，AOF 是 `BGREWRITEAOF`（log 太大時觸發）fork。兩個若同時跑，記憶體壓力疊加。

### AOF 的 fsync 策略決定丟多少資料

AOF 寫 log 分兩步：先 write 到 OS 的 page cache，再 fsync 刷到磁碟。`appendfsync` 控制 fsync 頻率，這是持久性與延遲的核心旋鈕：

| `appendfsync` | fsync 時機        | 崩潰最多丟          | 延遲影響                 |
| ------------- | ----------------- | ------------------- | ------------------------ |
| `always`      | 每個寫命令        | 幾乎不丟            | 每次寫都等磁碟、延遲最高 |
| `everysec`    | 每秒一次（背景）  | 最多 1 秒           | 多數場景的平衡點（預設） |
| `no`          | 交給 OS（~30 秒） | OS 決定、可能丟很多 | 延遲最低、持久性最弱     |

`everysec` 是多數場景的預設選擇——背景執行緒每秒 fsync，主執行緒不等磁碟，崩潰最多丟 1 秒。但要注意：當磁碟 I/O 飽和，背景 fsync 跑超過 1 秒沒完成，主執行緒會被迫等待（避免 buffer 無限堆積），這時延遲尖峰跟 `always` 一樣明顯。

### 混合持久化：RDB preamble + AOF tail

Redis 4.0 後的 `aof-use-rdb-preamble yes`（4.0+ 預設開）把兩者結合：AOF rewrite 時，先寫一段 RDB 格式的快照當前綴，後面接增量命令 log。還原時先快速載入 RDB preamble，再重放尾端的 log。這拿到了 RDB 的還原速度與 AOF 的細顆粒持久性，是目前的建議配置。

## 配置：持久化的設定路徑

```bash
# --- RDB snapshot 規則（多久 + 多少改動觸發 BGSAVE）---
# redis.conf:
#   save 900 1      # 900 秒內有 1 個 key 改動
#   save 300 100    # 300 秒內有 100 個改動
#   save 60 10000   # 60 秒內有 10000 個改動
# 純 cache 不需要 RDB 可關閉：
#   save ""

# --- AOF 設定 ---
redis-cli CONFIG SET appendonly yes
redis-cli CONFIG SET appendfsync everysec
# AOF rewrite 觸發條件：比上次 rewrite 大 100% 且至少 64MB
redis-cli CONFIG SET auto-aof-rewrite-percentage 100
redis-cli CONFIG SET auto-aof-rewrite-min-size 64mb
# 混合持久化（4.0+ 預設）
redis-cli CONFIG SET aof-use-rdb-preamble yes
```

降低 fork 衝擊的兩個系統層設定：

```bash
# 1. 關閉 Transparent Huge Pages（THP）——THP 會讓 copy-on-write 以 2MB 為單位複製、放大 fork 後的記憶體與延遲
echo never > /sys/kernel/mm/transparent_hugepage/enabled

# 2. 允許 overcommit memory——fork 時 Linux 預設可能因 overcommit 檢查拒絕 fork、導致 BGSAVE 失敗
# /etc/sysctl.conf:
#   vm.overcommit_memory = 1
```

這兩個是 Redis 官方明確建議的系統設定，沒設好會直接讓 fork 失敗或放大延遲尖峰。

## Production 故障演練

### Case 1：BGSAVE 那一刻 p99 延遲尖峰

**徵兆**：監控上每隔一段時間（對齊 save 規則）出現規律的延遲尖峰，p99 從 2ms 跳到 300-800ms，持續一兩秒後恢復。`INFO stats` 的 `latest_fork_usec` 顯示某次 fork 花了 700000 微秒（0.7 秒）。

**根因**：大記憶體實例的 `fork()` 要複製分頁表，這個動作阻塞主執行緒。實例越大尖峰越明顯，THP 開著會更嚴重。

**修法**：

1. 確認 THP 關閉（最常見的放大原因）
2. 把 RDB save 規則放寬或關閉——純 cache 場景靠 AOF 或乾脆不持久化
3. 大實例考慮分片，把單實例記憶體降下來，fork 成本隨之降低
4. 在 replica 上做持久化（master 只服務、replica 負責 BGSAVE），把 fork 尖峰移出服務路徑

### Case 2：fork 期間記憶體翻倍觸發 OOM

**徵兆**：BGSAVE 開始後記憶體快速上升，`used_memory_rss` 在 snapshot 期間衝高，撞到機器 RAM 上限，Linux OOM killer 把 redis-server 進程 SIGKILL，無預警下線。

**根因**：copy-on-write 在寫入密集期間複製大量分頁，maxmemory 沒留足夠 headroom。maxmemory 設成 RAM 的 90%+ 時，fork 期間的分頁複製把 RSS 推爆系統。

**修法**：

1. maxmemory 設成 RAM 的 60-70%，留 30-40% 給 fork copy-on-write（寫入越密集留越多）
2. 設 `vm.overcommit_memory = 1` 避免 fork 直接被拒
3. 在低寫入時段（夜間）排程 BGSAVE，減少 fork 期間被複製的分頁
4. 監控 `latest_fork_usec` 與 BGSAVE 期間的 RSS 峰值，跟 [記憶體調校](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/)的 headroom 計算合看

### Case 3：AOF everysec 在磁碟飽和時退化成 always

**徵兆**：平常延遲穩定，某段時間（通常伴隨大量寫入或磁碟被其他進程佔用）延遲全面上升，`INFO` 的 `aof_delayed_fsync` 計數持續增加。

**根因**：`everysec` 的背景 fsync 應該每秒完成，但磁碟 I/O 飽和時 fsync 跑超過 1 秒。Redis 為了不讓 AOF buffer 無限堆積，會在主執行緒上阻塞等 fsync 完成——`everysec` 在這個情境下退化成接近 `always` 的延遲行為。

**修法**：

1. 用獨立的高 IOPS 磁碟給 AOF（不要跟 OS / log / 其他服務共用 I/O）
2. 監控 `aof_delayed_fsync`，持續增加代表磁碟跟不上寫入
3. 評估 `no-appendfsync-on-rewrite yes`——AOF rewrite 期間暫停 fsync，避免 rewrite 的 I/O 跟 fsync 互搶（代價是 rewrite 期間崩潰丟更多）
4. 寫入吞吐超過單磁碟負荷是擴容訊號，不是調 fsync 能解

### Case 4：AOF 檔尾損壞讓 Redis 起不來

**徵兆**：Redis 崩潰後重啟失敗，log 顯示 `Bad file format reading the append only file`，服務無法載入 AOF。

**根因**：崩潰發生在 AOF 寫到一半，最後一條命令只寫了部分 byte，AOF 檔尾不完整。Redis 預設 `aof-load-truncated yes` 應能容忍尾端截斷，但若損壞在中段（罕見的磁碟錯誤）或設了 `aof-load-truncated no`，載入直接失敗。

**修法**：

1. 確認 `aof-load-truncated yes`（預設），容忍尾端截斷自動修復
2. 中段損壞用 `redis-check-aof --fix appendonly.aof` 修復（會截掉損壞點之後的內容、有資料遺失）
3. 修復前先備份原 AOF 檔，不要直接覆蓋
4. 混合持久化下還原優先用 RDB preamble，降低純 AOF replay 的損壞風險

### Case 5：以為有持久化、其實 BGSAVE 一直在失敗

**徵兆**：某次需要從 RDB 還原時發現 `dump.rdb` 是好幾天前的，期間的資料全沒了。回查 log 發現 BGSAVE 一直報 `Can't save in background: fork: Cannot allocate memory`。

**根因**：`vm.overcommit_memory` 是預設的 0，Linux 在 fork 時做嚴格的記憶體檢查——當 Redis 已用掉大半 RAM，fork 估算可能需要翻倍記憶體而被拒。BGSAVE 靜默失敗，RDB 停留在最後一次成功的版本，但沒人在看 log。

**修法**：

1. 設 `vm.overcommit_memory = 1`，讓 fork 在記憶體吃緊時仍能成功（靠 copy-on-write 實際不會真的翻倍）
2. 監控 `rdb_last_bgsave_status` 與 `aof_last_bgrewrite_status`，`err` 要立刻告警
3. 監控 `rdb_last_save_time`，距今太久代表持久化已停擺
4. 持久化的存在不等於可用——定期演練從備份還原，驗證 RDB / AOF 真的能載入

## Capacity / cost 邊界

持久化的容量判讀，圍繞 fork 成本與磁碟負荷：

| 訊號                     | 健康區間                    | 警戒與動作                                      |
| ------------------------ | --------------------------- | ----------------------------------------------- |
| `latest_fork_usec`       | < 100ms（小實例）           | > 數百 ms → 實例太大、考慮分片或 replica 持久化 |
| fork 期間 RSS 峰值       | < 機器 RAM                  | 接近 RAM → maxmemory headroom 不足              |
| `aof_delayed_fsync`      | 接近 0                      | 持續增加 → 磁碟 I/O 跟不上、換高 IOPS 磁碟      |
| `rdb_last_bgsave_status` | `ok`                        | `err` → fork 失敗、查 overcommit / 記憶體       |
| AOF 檔大小 / dataset     | rewrite 後接近 dataset 大小 | 遠大於 dataset → rewrite 沒觸發、檢查閾值       |

撞牆後的路由判斷：

- **fork 尖峰無法接受、實例又必須大**：把持久化移到 replica（master 純服務），或走 [Cluster 分片](/backend/02-cache-redis/vendors/redis/cluster-resharding/)降低單實例記憶體。
- **大記憶體下 fork 成本是結構性瓶頸**：[DragonflyDB](/backend/02-cache-redis/vendors/dragonflydb/) 用 fork-less snapshot 機制，大記憶體場景的快照不付 fork 的延遲與記憶體翻倍代價——若 fork 尖峰是主要痛點，這是值得評估的架構替代。
- **需要真正的 source-of-truth 持久性（不是盡力而為）**：Redis 持久化本質是 cache 的回填保險，不是交易級持久性。要強持久性走 [MemoryDB](/backend/02-cache-redis/vendors/aws-elasticache/)（multi-AZ transaction log）或 [database 模組](/backend/01-database/)。

## 整合 / 下一步

持久化決策的起點其實是一個選型問題：這份資料是 cache 還是 source-of-truth。

- **跟 [記憶體調校](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/)**：fork 的 copy-on-write 是 maxmemory headroom 的主要消耗者，兩者必須一起算。
- **跟 [replication / failover](/backend/02-cache-redis/vendors/redis/sentinel-ha-failover/)**：replica 是承接持久化負擔的地方，也是 fork 尖峰的替代執行點。
- **跟 [Tubi 的 cache vs durable 選型](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/)**：Tubi 把 ML feature store 從 ScyllaDB（durable）遷到 ElastiCache，判斷是「feature 可重新計算」——這正是「不需要持久化」的判斷，持久化配置應隨之簡化甚至關閉。反過來，若資料不可重建，問題在選錯儲存層，不在持久化調校。
- **跟 [cache copy boundary](/backend/02-cache-redis/cache-copy-freshness-boundary/)**：服務若把 Redis 當主要 serving layer，持久化決定了重啟後是冷啟動回源雪崩還是溫啟動，跟 stampede 防護直接相關。

## 相關連結

- 上游 vendor 頁：[Redis](/backend/02-cache-redis/vendors/redis/)
- 同 vendor deep article：[記憶體與淘汰調校](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/)、[Cluster re-sharding](/backend/02-cache-redis/vendors/redis/cluster-resharding/)
- 上游概念：[2.7 cache copy boundary](/backend/02-cache-redis/cache-copy-freshness-boundary/)
- Methodology：[Vendor 深度技術文章寫作方法論](/posts/vendor-deep-article-methodology/)
