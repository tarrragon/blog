---
title: "KeyDB active-active 多主複製：last-write-wins 會默默吃掉哪一筆寫入"
date: 2026-06-16
description: "KeyDB 的 active-active 讓兩個 master 都能寫、互相同步，聽起來解決了跨區寫入的所有問題——直到兩邊同時寫同一個 key，last-write-wins 默默丟掉其中一筆。本文展開 active-active 的複製機制與衝突語意、實機驗證雙向同步、5 個把多主複製寫成資料遺失與迴圈的 production 踩坑，以及哪些資料能放 active-active、哪些不能的邊界"
weight: 11
tags: ["backend", "cache", "keydb", "active-active", "replication", "deep-article"]
---

> 本文是 [KeyDB](/backend/02-cache-redis/vendors/keydb/) overview 的 implementation-layer deep article。選型層（KeyDB vs Redis / DragonflyDB / Valkey、為何選 fork）見 overview；本文只處理「決定用 KeyDB active-active 後，衝突與一致性怎麼判」。命令實機驗證於 eqalpha/keydb image、最後檢查日 2026-06-16；複製機制以 [KeyDB active-replication 文件](https://docs.keydb.dev/docs/active-rep/) 為準。

## 兩邊都能寫，聽起來太美好

Redis 的複製是單向的：一個 master 寫、replica 唯讀。要跨區讓兩邊都能就近寫入，Redis 本身做不到（得靠應用層分區或外部工具）。KeyDB 的 active-active 把這個限制拿掉——兩個（含以上）KeyDB 節點都是 master、都能接受寫入、互相把寫入同步給對方。對「兩個 region 都要低延遲寫入同一份 cache」的場景，這聽起來解決了所有問題。

問題藏在「兩邊同時寫同一個 key」的那一刻。active-active 沒有全域協調者來仲裁誰對誰錯，它用 last-write-wins（LWW）：比較兩筆寫入的時間戳，留下較晚的、默默丟掉較早的。多數時候沒事，但當兩個 region 在幾毫秒內各自更新同一個 key，其中一筆寫入會無聲消失——沒有錯誤、沒有日誌、application 以為自己寫成功了。

理解 KeyDB active-active 就是理解這個取捨：它用 LWW 換到了「兩邊都能寫」的可用性，代價是放棄了強一致與「不丟寫入」的保證。本文展開複製機制、衝突語意，以及哪些資料放得進這個模型、哪些放進去就是 bug。

## 核心概念：active-active 的複製與衝突語意

active-active 不是「分散式交易」，它是「雙向非同步複製 + LWW 衝突解決」。理解它要抓三個點：

**每個節點都是 active-replica**。一般 Redis replica 是唯讀的；KeyDB 的 active-replica 既接受本地寫入、又接收對方的複製流。兩個節點互相設定對方為 master，形成雙向複製環。實機看到的 role 就是 `active-replica`（不是 master / slave）。

**複製是非同步的**。本地寫入立即回 OK 給 client，之後才非同步傳給對方節點。這意味著兩個節點之間永遠有一個複製延遲窗口——在這個窗口內，兩邊看到的資料可能不同。這是 active-active 是 AP（可用性 + 分區容忍）而非 CP 的根本原因。

**衝突用 last-write-wins 解決**。同一個 key 在兩個節點被並發修改時，KeyDB 比較版本（基於時間戳），保留較晚的寫入、丟棄較早的。沒有 merge、沒有 vector clock、沒有 application callback——就是時間戳比大小。時鐘不同步（clock skew）會直接影響哪一筆被判定為「較晚」。

**每筆寫入帶來源標記避免無限迴圈**。A 的寫入同步給 B 後，B 不會再把它當成新寫入傳回 A（否則會無限循環）。KeyDB 用來源標記處理這個，但複製拓樸設計錯（例如環狀多節點）仍可能放大流量。

## 配置：兩節點 active-active 的設定路徑

實機驗證的最小雙主設定（兩個節點互相複製）：

```bash
# 節點 A 與 B 都開 active-replica + multi-master
docker run -d --name kdb-a --network kdbnet -p 6401:6379 \
  eqalpha/keydb keydb-server --active-replica yes --multi-master yes
docker run -d --name kdb-b --network kdbnet -p 6402:6379 \
  eqalpha/keydb keydb-server --active-replica yes --multi-master yes

# 互相指向對方（形成雙向複製）
keydb-cli -p 6401 replicaof kdb-b 6379
keydb-cli -p 6402 replicaof kdb-a 6379
```

實機驗證雙向同步（最後檢查日 2026-06-16）：

```bash
# 寫 A、讀 B
keydb-cli -p 6401 SET fromA hello   # → OK
keydb-cli -p 6402 GET fromA         # → hello   （A 的寫入同步到 B）

# 寫 B、讀 A（雙向）
keydb-cli -p 6402 SET fromB world   # → OK
keydb-cli -p 6401 GET fromB         # → world   （B 的寫入同步到 A）

# 確認 role 與複製鏈路
keydb-cli -p 6401 INFO replication | grep -E "role|master_link_status|connected_slaves"
# role:active-replica
# master_link_status:up
# connected_slaves:1
```

兩個節點都回報 `role:active-replica`（不是傳統的 master / slave），`master_link_status:up` 確認複製鏈路健康。寫入任一節點、另一節點都讀得到，這就是 active-active 的核心行為。

## Production 故障演練

### Case 1：並發寫同一 key、一筆寫入無聲消失

**徵兆**：兩個 region 的 application 各自更新同一個 user 的 cache（例如 profile），事後發現其中一個 region 的更新「沒生效」——但寫入時 application 收到的是 OK，沒有任何錯誤。

**根因**：active-active 的 LWW。兩筆寫入在複製延遲窗口內並發發生，KeyDB 比較時間戳保留較晚的、默默丟棄較早的。application 兩邊都以為自己寫成功了（本地確實 OK），但同步後只有一筆存活。

**修法**：

1. 不要讓同一個 key 被多個 region 並發寫——按 key 分區（user X 的寫入永遠路由到 region A），把多主退化成「就近讀 + 單點寫」
2. 真的需要多點寫的計數器類資料，用 CRDT 語意的結構（KeyDB 的 LWW 不適合 counter，並發 INCR 會互相覆蓋而非累加）
3. 接受 LWW 是 cache 的取捨——可重建的 cache 副本丟一筆寫入可回源重算，不可重建的資料不該放 active-active
4. 衝突無聲是最危險的——加應用層的寫入審計（不靠 KeyDB 告警）

### Case 2：clock skew 讓「較晚」的判定錯亂

**徵兆**：明明 region B 後寫的值，最後存活的卻是 region A 先寫的值——LWW 的「後寫者勝」失效。

**根因**：LWW 比較時間戳，但兩個節點的系統時鐘若沒同步（clock skew），「較晚」的判定就錯了。B 的時鐘慢了 200ms，B 後寫的值帶的時間戳反而比 A 早，被判定為「較舊」丟棄。

**修法**：

1. 所有 KeyDB 節點強制 NTP 時鐘同步，把 skew 壓到毫秒級
2. 監控節點間的時鐘偏差，skew 超過複製延遲就有 LWW 判定錯亂風險
3. 對時間敏感的衝突，LWW 本質不可靠——時鐘永遠無法完美同步，這是 LWW 模型的固有弱點
4. 需要正確衝突解決的場景，不要用 LWW 的 active-active，改強一致儲存

### Case 3：複製延遲下的 stale read

**徵兆**：region A 寫入後，立刻有請求打到 region B 讀同一 key，讀到舊值；幾百毫秒後再讀才是新值。

**根因**：active-active 是非同步複製，A 的寫入要經過網路傳到 B 才可見。在這個複製延遲窗口內，B 讀到的是 stale 值。跨 region 的延遲窗口比同 AZ 大得多。

**修法**：

1. 寫後需要立即一致讀的路徑，讀同一個寫入的節點（read-your-writes 綁定到寫入 region）
2. 監控節點間複製延遲，跨 region 的延遲是 stale window 的下界
3. 接受最終一致——這是 active-active 的本質，cache 場景多數可容忍短暫 stale
4. 不可容忍 stale 的資料不適合 active-active，走單寫入點 + 跨區唯讀 replica

### Case 4：複製拓樸設計錯、流量放大或迴圈

**徵兆**：加了第三個 active 節點組成環狀後，節點間流量異常放大、CPU 升高，甚至同一筆寫入被反覆傳遞。

**根因**：active-active 多節點（> 2）的拓樸需要小心設計。全互連（full mesh）下每筆寫入要傳給所有其他節點、流量隨節點數平方成長；環狀拓樸若來源標記處理不當可能放大傳遞。

**修法**：

1. 多節點 active-active 優先用 full mesh 但控制節點數（active-active 不適合大量節點）
2. 監控節點間複製流量，異常放大代表拓樸或來源標記問題
3. 大規模多區優先考慮「每區單寫入點 + 跨區唯讀」而非全 active-active
4. active-active 的甜蜜點是 2-3 個區的雙向就近寫，不是大規模 mesh

### Case 5：節點重連後的全量重同步衝擊

**徵兆**：一個節點短暫斷線後重連，重連瞬間 CPU / 網路尖峰，期間延遲升高。

**根因**：節點斷線時間過長、超過複製 backlog 能覆蓋的範圍，重連時要做全量重同步（full resync）——對方節點要產生快照（fork、見 [Redis persistence 的 fork 成本](/backend/02-cache-redis/vendors/redis/persistence-fork-latency/)，KeyDB 繼承 Redis 的 fork 機制）並傳輸整個 dataset。

**修法**：

1. 設足夠大的 `repl-backlog-size`，讓短暫斷線走部分同步（partial resync）而非全量
2. 重同步的 fork 成本跟記憶體 headroom 相關，節點要留 fork 空間
3. 監控 `master_link_status`，頻繁 down / up 代表網路不穩、要先修網路
4. 跨 region 的 active-active 對網路穩定性敏感，不穩的鏈路會頻繁觸發重同步

## Capacity / cost 邊界

active-active 的容量判讀，核心在衝突率與複製健康：

| 訊號                    | 健康區間                    | 警戒與動作                               |
| ----------------------- | --------------------------- | ---------------------------------------- |
| 同 key 跨節點並發寫入率 | 接近 0（key 按區分區）      | 高 → LWW 丟寫入風險、改 key 分區         |
| 節點間 clock skew       | < 複製延遲（毫秒級）        | 大 → LWW 判定錯亂、強制 NTP              |
| 節點間複製延遲          | 跨 region 可接受的 stale 窗 | 過大 → stale read 嚴重、檢查網路         |
| `master_link_status`    | `up`                        | 頻繁 down → 網路不穩、會觸發重同步       |
| active 節點數           | 2-3（雙向就近寫）           | 過多 → mesh 流量平方成長、改單寫入點拓樸 |

撞牆後的路由判斷：

- **需要正確的衝突解決 / 不能丟寫入**：LWW 不保證，走強一致儲存（[database 模組](/backend/01-database/) 的 multi-region 一致性方案）或單寫入點架構。
- **需要 counter / 累加語意的多點寫**：LWW 會讓並發 INCR 互相覆蓋，KeyDB active-active 不適合，改 CRDT 或單點 counter。
- **跨 region 但可接受單寫入點**：用 Redis / Valkey 的單向複製（一區寫、其他區唯讀），比 active-active 簡單且無衝突。
- **大規模多區**：active-active 的甜蜜點是 2-3 區，更大規模走 managed 的跨區方案（[ElastiCache Global Datastore](/backend/02-cache-redis/vendors/aws-elasticache/) 的 active-passive）。

## 整合 / 下一步

active-active 是 KeyDB 區別於 Redis 的核心能力之一，但它的取捨跨多個子系統：

- **跟 [KeyDB overview](/backend/02-cache-redis/vendors/keydb/)**：overview 點到 active-active 是 last-write-wins、本文展開它什麼時候默默丟資料。
- **跟 [Redis persistence / fork latency](/backend/02-cache-redis/vendors/redis/persistence-fork-latency/)**：KeyDB 繼承 Redis 的 fork 機制，節點重連的全量重同步付 fork 成本。
- **跟 [cache copy boundary](/backend/02-cache-redis/cache-copy-freshness-boundary/)**：active-active 的 stale window 與 LWW 丟寫入，本質是「cache 副本的新鮮度與一致性邊界」議題的多主版本。
- **跟 [Snap KeyDB cross-cloud case](/backend/09-performance-capacity/cases/snap-gcp-keydb-cross-cloud/)**：Snap 用 KeyDB 的主因是 cross-cloud latency 治理（cache 與 application 共置），active-active 的雙向就近寫是這類 multi-cloud 場景的工具，但要按 key 分區避開 LWW 衝突。

## 相關連結

- 上游 vendor 頁：[KeyDB](/backend/02-cache-redis/vendors/keydb/)
- 對照 vendor：[DragonflyDB 多核架構](/backend/02-cache-redis/vendors/dragonflydb/shared-nothing-multicore-architecture/)、[Redis Sentinel failover](/backend/02-cache-redis/vendors/redis/sentinel-ha-failover/)（單向複製的 HA）
- 上游概念：[2.7 cache copy boundary](/backend/02-cache-redis/cache-copy-freshness-boundary/)
- Methodology：[Vendor 深度技術文章寫作方法論](/posts/vendor-deep-article-methodology/)
