---
title: "Memcached slab allocator 與記憶體經濟學：明明有記憶體卻在 evict"
date: 2026-06-16
description: "Memcached 用 slab allocator 預切記憶體成固定大小的 chunk，這讓它永不碎片化、卻會在還有大量空閒記憶體時就開始淘汰——slab calcification。本文展開 slab class、growth_factor、page 分配的會計模型、5 個把 slab 機制寫成記憶體浪費與淘汰事故的 production 踩坑，以及純 KV 邊界與多執行緒擴展的判讀"
weight: 11
tags: ["backend", "cache", "memcached", "slab-allocator", "memory", "deep-article"]
---

> 本文是 [Memcached](/backend/02-cache-redis/vendors/memcached/) overview 的 implementation-layer deep article。選型層（純 KV vs Redis data types、何時選 Memcached）見 overview；本文只處理「決定用 Memcached 後，slab 記憶體怎麼配才不會莫名淘汰」。命令實機驗證於 `memcached:1.6`（VERSION 1.6.42）、最後檢查日 2026-06-16；機制以 [Memcached 官方 wiki](https://github.com/memcached/memcached/wiki/UserInternals) 為準。

## 明明有記憶體、卻在 evict

Memcached 最違反直覺的故障是這樣：監控顯示 `evictions` 持續上升、hit rate 在掉，但 `stats` 算下來實際用掉的記憶體遠低於 `-m` 設的上限——機器明明還有空間，Memcached 卻在淘汰資料。換成 Redis 思維的人會卡住，因為 Redis 是一個共用的記憶體池，不會出現「有空間卻淘汰」。

這個現象叫 slab calcification，根因在 Memcached 的記憶體模型：它把記憶體預先切成許多固定大小的格子（slab class），每個 class 各自管自己那塊，跟 Redis 共用一個記憶體池的模型相反。記憶體一旦分配給某個 class，預設不會還回去給別的 class 用。如果你的 value 大小分布隨時間改變（早期都是小 value、後來都是大 value），早期被小 value 佔走的記憶體還鎖在小 class 裡，大 value 的 class 沒有足夠空間、開始淘汰——即使整體還有大量「屬於別人」的空閒記憶體。

理解 Memcached 就是理解這套 slab 經濟學。它用「放棄記憶體的靈活性」換到了「永不碎片化、O(1) 分配、可預測的多執行緒擴展」。這個取捨在純 cache 場景非常划算，但它的失敗模式跟 Redis 完全不同，要用 slab 的語言來判讀。

## 核心概念：slab allocator 的會計模型

Memcached 啟動時不會把 `-m` 指定的記憶體一次配掉，而是按需求以 **page**（預設 1MB）為單位分配給 **slab class**，每個 class 存放某個大小區間的 item。

**slab class 與 chunk size**。每個 slab class 對應一個固定的 chunk size，item 被放進「裝得下它的最小 class」。class 的 chunk size 按 `growth_factor` 等比成長——實機看預設值：

```bash
printf 'stats settings\r\nquit\r\n' | nc localhost 11211 | grep growth_factor
# STAT growth_factor 1.25

printf 'set k1 0 0 5\r\nhello\r\nstats slabs\r\nquit\r\n' | nc localhost 11211 | grep -E "chunk_size|active_slabs"
# STAT 1:chunk_size 96      ← 最小的 slab class、chunk 96 bytes
# STAT active_slabs 1
```

`growth_factor 1.25` 表示每個 class 的 chunk size 是前一個的 1.25 倍：class 1 是 96 bytes、class 2 約 120、class 3 約 152……一路到 item 大小上限。一個 100 bytes 的 value 放不進 96 bytes 的 class 1，被放進 120 bytes 的 class 2——浪費 20 bytes。這個「向上取整到 chunk size」的浪費是 slab 模型的固有成本。

**page 分配是單向的**。當某個 class 需要空間，Memcached 給它一個 1MB 的 page，切成該 class 的 chunk。這個 page 預設永久屬於這個 class——這就是 calcification 的來源。`-o slab_automove` 與手動 `slabs reassign` 可以把 page 在 class 間搬移，但預設行為偏保守。

**LRU 是 per-slab-class 的**。淘汰不是全域的，是每個 slab class 維護自己的 LRU。所以「class 2 滿了開始淘汰、但 class 5 有空閒 page」是正常現象——淘汰看的是該 class 自己的空間，不是全域記憶體。

這三點合起來解釋了開頭的悖論：evict 發生在某個 class 內，跟全域剩餘記憶體無關。

## 配置：slab 與多執行緒的設定路徑

```bash
# 啟動參數（Memcached 的調校多在啟動參數、不像 Redis 有大量 runtime CONFIG SET）
docker run -d --name memcached -p 11211:11211 memcached:1.6 \
  memcached \
    -m 1024 \          # 記憶體上限 1024 MB
    -t 4 \             # worker thread 數（多執行緒、對齊 CPU 核數）
    -f 1.25 \          # slab growth factor（預設 1.25、調小→class 更密集→浪費更少但 class 更多）
    -I 2m \            # 單一 item 大小上限（預設 1MB、超過要調大或拆 value）
    -o slab_automove=1 # 自動把空閒 page 從一個 class 搬到吃緊的 class（緩解 calcification）
```

調校判讀：

- `-m` 是給 item 資料的上限，Memcached 自身的 hash table、連線 buffer 等 overhead 在 `-m` 之外，機器要留 headroom
- `-t` 對齊 CPU 核數——Memcached 從早期就是 multi-threaded，這是它跟早期單執行緒 Redis 的核心差異
- `-f` 調小（例如 1.08）讓 slab class 更密集、向上取整浪費更少，代價是 class 數變多、管理開銷略增
- `-I` 是單 item 上限，超過會 store 失敗（見故障演練 Case 3）
- `slab_automove=1` 是緩解 calcification 的關鍵，預設視版本而定，明確開啟較穩

## Production 故障演練

### Case 1：slab calcification——value 大小漂移造成假性記憶體不足

**徵兆**：`evictions` 上升、hit rate 下降，但 `stats` 顯示 `bytes` 遠低於 `limit_maxbytes`。`stats slabs` 看到某個 class 的 page 用滿在淘汰，另一個 class 有大量空閒 chunk。

**根因**：value 大小分布隨時間漂移。早期 value 小、記憶體被分配給小 slab class；後來 value 變大、需要大 class，但 page 已被小 class 鎖住不還，大 class 空間不足開始淘汰。整體記憶體沒滿，但「對的 class」沒空間。

**修法**：

1. 開 `-o slab_automove=1`，讓 Memcached 自動把空閒 page 從冷 class 搬到吃緊的 class
2. 手動觸發搬移：`slabs reassign <src_class> <dst_class>`（緊急救火用）
3. 監控 `stats slabs` 各 class 的 `used_chunks` vs `total_chunks` 與 `stats items` 的 per-class evicted，找出失衡的 class
4. 從源頭穩定 value 大小分布——序列化格式統一、避免同類資料時大時小

### Case 2：chunk 向上取整浪費大量記憶體

**徵兆**：存的 value 總大小算起來只有 600MB，但 Memcached 報用掉接近 1GB，記憶體效率異常低。

**根因**：value 大小剛好落在 slab class chunk size 的「上緣之外」，被向上取整到下一個更大的 class，每個 item 浪費接近一個 growth step 的空間。例如大量 130 bytes 的 value 被放進 152 bytes 的 class，每個浪費 22 bytes，量大就顯著。

**修法**：

1. `-f` 調小（1.25 → 1.08）讓 class 粒度更細，向上取整的浪費變小
2. `stats slabs` 看主要 class 的 `chunk_size` 跟你的 value 實際大小差多少，量化浪費
3. value 設計上靠近 chunk 邊界（例如壓縮或裁剪 metadata 讓 value 剛好塞進較小的 class）
4. 浪費是 slab 模型的固有成本，純 KV 的 trade-off——換到的是永不碎片化與 O(1) 分配

### Case 3：value 超過 item 大小上限、store 直接失敗

**徵兆**：某些大 value 的寫入回 `SERVER_ERROR object too large for cache`，application 端 cache 寫入靜默失敗、之後一直 miss。

**根因**：單一 item 超過 `-I` 設的上限（預設 1MB）。Memcached 設計上不適合存大 object，預設 1MB 是刻意的純 cache 邊界。

**修法**：

1. 確認 value 大小分布，大 value 是否真該進 Memcached（純 KV cache 不適合大 blob）
2. 必要時調大 `-I`（例如 `-I 2m`），但這會改變 slab class 結構、增加大 chunk 的記憶體佔用
3. 大 object 考慮壓縮、或拆成多個小 key、或改放適合的儲存（物件儲存 / [Redis](/backend/02-cache-redis/vendors/redis/) 的 hash）
4. application 端要處理 store 失敗，不要假設 set 一定成功——失敗就走 origin

### Case 4：thread 數設太高、lock contention 反而拖慢

**徵兆**：把 `-t` 從 4 調到 32 想榨多核效能，throughput 沒升反降，CPU 在 system time 飆高。

**根因**：Memcached 的多執行緒有 per-item lock（hash bucket lock），thread 數遠超核數時，執行緒互搶 lock 與 CPU、context switch 開銷超過平行收益。

**修法**：

1. `-t` 對齊實體核數，不要超配（多數場景 4-8 已足夠，極高核機器再往上調並壓測）
2. 用實際 workload 壓測對比不同 `-t` 的 throughput，找拐點
3. hot key 集中時 lock contention 更明顯（同 bucket），這是資料分布問題不是 thread 數問題
4. 跨機器水平擴展（client-side consistent hashing）比單機堆 thread 更能解規模，見本文整合段

### Case 5：連線數打到上限、新連線被拒

**徵兆**：高並發下新連線報錯或 hang，`stats` 的 `curr_connections` 接近 `max_connections`，`listen_disabled_num` 在增加。

**根因**：每個 client 連線佔一個 connection slot，Memcached 預設 `-c 1024`。大量 client（尤其沒用連線池、每請求建連）會打滿 connection 上限。

**修法**：

1. client 端用連線池重用連線，不要每請求建連
2. 調高 `-c`（例如 `-c 4096`），但連線本身有記憶體 overhead（在 `-m` 之外），要算進機器容量
3. 監控 `curr_connections` 與 `listen_disabled_num`，後者非零代表曾達上限拒絕連線
4. 連線數爆炸常是 client fan-out 問題，跨多 Memcached node 分散（consistent hashing）能攤平單 node 連線壓力

## Capacity / cost 邊界

Memcached 的容量判讀，核心在 slab 效率與多執行緒擴展：

| 訊號                           | 健康區間                     | 警戒與動作                                           |
| ------------------------------ | ---------------------------- | ---------------------------------------------------- |
| `evictions` 速率               | 接近 0（working set 放得下） | 持續高但記憶體沒滿 → calcification、開 slab_automove |
| 各 class `used / total chunks` | 各 class 均衡                | 單 class 滿、其他空 → calcification                  |
| chunk 向上取整浪費             | 小（value 貼近 chunk size）  | 大 → 調小 `-f` 或調整 value 大小                     |
| `curr_connections / -c`        | < 80%                        | 接近上限 → 用連線池或調高 `-c`                       |
| 多執行緒 CPU                   | 核數內、system time 低       | system time 高 → `-t` 超配、lock contention          |

撞牆後的路由判斷：

- **需要 data types / 持久化 / distributed lock**：Memcached 是純 KV、刻意不做這些。需要這些走 [Redis / Valkey](/backend/02-cache-redis/vendors/redis/)，這是 capability 差異不是調校能補。
- **單機容量 / throughput 不夠**：Memcached 沒有 server-side cluster，靠 client-side consistent hashing（ketama）水平擴展到多 node，見整合。
- **想要 Memcached 的多執行緒 + Redis 的 data types**：[DragonflyDB](/backend/02-cache-redis/vendors/dragonflydb/) 兼具多核與 Redis 相容，是兩者的中間點。

## 整合 / 下一步

Memcached 的單機很簡單，它的工程深度在「如何把多個 Memcached node 組成一個 cache 層」——而這發生在 client 端與代理層，不在 server：

- **client-side consistent hashing（ketama）**：Memcached server 之間互不知道彼此，sharding 由 client library 用 consistent hashing 決定 key 去哪個 node，加減 node 時最小化 key 重新分布。這是 Memcached 水平擴展的基礎。
- **跟 [Meta mcrouter](/backend/02-cache-redis/cases/meta-mcrouter-global-cache-routing/)**：Meta 的 mcrouter 是 Memcached 專屬的 protocol-aware routing proxy，把跨叢集 / 跨區的流量收斂、失效隔離、pool 管理從 client 端移到代理層——這是 Memcached 大規模治理的標準答案。
- **跟 [Netflix EVCache](/backend/02-cache-redis/cases/netflix-evcache-global-cache-layer/)**：EVCache 基於 Memcached，Netflix 在上面加跨 AZ replication 與 client-side smart routing，補足 Memcached 沒有的跨區 HA。
- **跟 [Meta TAO](/backend/02-cache-redis/cases/meta-tao-social-graph-cache-evolution/)**：TAO 底層用 Memcached 作為 social graph 的 cache 層，上層加一致性與關聯查詢——展示了純 KV 之上如何疊加語意。
- **跟 [Meta CacheLib + Kangaroo](/backend/02-cache-redis/cases/meta-cachelib-kangaroo-tiered-cache/)**：當 DRAM 的記憶體經濟撞到極限，Meta 用 CacheLib 把 cache 分層到 flash——這是 slab 記憶體經濟學的下一個邊界。

## 相關連結

- 上游 vendor 頁：[Memcached](/backend/02-cache-redis/vendors/memcached/)
- 對照 vendor：[Redis 記憶體與淘汰調校](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/)（jemalloc 池 vs slab class 的差異）、[DragonflyDB](/backend/02-cache-redis/vendors/dragonflydb/)
- 相關 migration：[Redis → Memcached](/backend/02-cache-redis/vendors/redis/migrate-to-memcached/)
- Methodology：[Vendor 深度技術文章寫作方法論](/posts/vendor-deep-article-methodology/)
