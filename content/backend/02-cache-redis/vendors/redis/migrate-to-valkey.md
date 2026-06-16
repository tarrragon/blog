---
title: "Redis → Valkey：同一份程式碼、不同授權的 drop-in 遷移"
date: 2026-06-16
description: "Valkey 是 Redis 7.2.4 的 fork，bit-for-bit 幾乎同源、RDB/AOF 檔案相容、client 一行不改——這是技術上最容易的 cache 遷移。真正的工作不在搬資料，在授權合規驗證與 fork 後分歧（Redis 7.4+ 功能、Stack 商業 module）的盤點。本文走 Type B drop-in、相容性 audit 前置、5 個把『最容易的遷移』寫成事故的踩坑"
weight: 11
tags: ["backend", "cache", "redis", "valkey", "migration", "drop-in"]
---

> 本文是跨 vendor migration playbook、cross-link 到 [Redis](/backend/02-cache-redis/vendors/redis/)（source）跟 [Valkey](/backend/02-cache-redis/vendors/valkey/)（target）。跑 6 維 diff dimension audit 後判定為 **Type B drop-in**（全維度 Low），結構走 6-section + 相容性 audit 前置。實機驗證於 valkey/valkey:8（valkey_version 8.1.8、redis_version 7.2.4）、最後檢查日 2026-06-16。

## 同一份程式碼、不同授權

多數 migration 的工作量在「source 跟 target 不一樣」——schema 要翻譯、API 要改、資料要轉。Redis → Valkey 幾乎沒有這個問題：Valkey 是 2024 年從 Redis 7.2.4 直接 fork 出來的，那一刻它跟 Redis 是 bit-for-bit 同一份程式碼。RDB 與 AOF 檔案格式相同（可以直接把 Redis 的資料目錄拷給 Valkey 載入）、RESP 協定相同、所有 Redis client library 不改一行就能連。技術上，這是 cache 領域最容易的遷移。

那為什麼要寫一篇 playbook？因為這個遷移的工作量不在資料層，在兩個別的地方。第一是**授權**——Redis 2024 改成 RSALv2 / SSPL（非 OSI 認可），Valkey 是 BSD 3-clause（OSI、Linux Foundation 治理），這個遷移的整個 driver 是授權合規，而合規驗證有它自己的流程。第二是**fork 後的分歧**——fork 那一刻兩者相同，但之後各自演進：Redis 加了 7.4+ 的新功能、Valkey 加了自己的（如 8.x 多執行緒），用到 fork 之後 Redis 新功能的部署會有相容缺口。

`INFO server` 上看得到這個「同源但分歧」的事實：

```bash
valkey-cli INFO server | grep -E "redis_version|valkey_version"
# redis_version:7.2.4    ← fork 點、client 以此判斷相容性（裝成 Redis 7.2.4）
# valkey_version:8.1.8   ← Valkey 自己的演進線
```

`redis_version:7.2.4` 是相容性的保證（client 看到就以 Redis 7.2.4 行為運作）；`valkey_version` 是分歧的證據。這篇 playbook 處理的就是「資料層幾乎零工作、工作在授權與分歧盤點」的 drop-in 遷移。

## 6 維 diff dimension audit：為什麼是 Type B

跑 diff dimension audit，Redis → Valkey 全維度 Low：

| 維度                   | 評估                                       | 等級 |
| ---------------------- | ------------------------------------------ | ---- |
| Schema / API           | 同 Redis 7.2.4（fork 同源）、RESP 協定一致 | Low  |
| Operational model      | 同 redis.conf、同監控指標、同 CLI 命令     | Low  |
| Abstraction / paradigm | 完全相同（同一份 code base 演進）          | Low  |
| Number of components   | 1 → 1（單服務換單服務）                    | Low  |
| Application change     | 零（所有 Redis client library 直接相容）   | Low  |
| Data topology          | RDB / AOF 檔案相容、可直接拷資料目錄       | Low  |

全 Low → **Type B drop-in**（6-section + 相容性 audit 前置、週期 1-4 週）。跟同模組的 [Redis → DragonflyDB](/backend/02-cache-redis/vendors/redis/migrate-to-dragonflydb/) 對照：DragonflyDB 是 C++ 重寫（drop-in 但 Lua / encoding / module 有差異），Valkey 是 fork（同源、連 RDB 檔都相容）——Valkey 的相容度比 DragonflyDB 更高，是 Type B 裡最純粹的一端。

這個遷移的特殊之處是 driver 在資料層之外：它是**授權 / 合規驅動**。依 [migration 方法論](/posts/migration-playbook-methodology/) 的漏類處理，政策 / 合規驅動的遷移資料層仍走 Type B，但 audit 重點多一塊**授權驗證與證據收集**。

## 相容性 audit：cutover 前要確認的清單

Valkey 號稱 100% 相容 Redis 7.2.4，但「100%」的邊界在 fork 之後的分歧。Pre-migration 必跑的 audit：

| Redis feature                          | Valkey 相容程度                                  | Action                                    |
| -------------------------------------- | ------------------------------------------------ | ----------------------------------------- |
| Core data types / commands / RESP      | 完全相容（fork 自 7.2.4）                        | 無需處理                                  |
| RDB / AOF 檔案格式                     | 完全相容（可直接拷資料目錄）                     | 無需轉檔                                  |
| Eviction / persistence / pub-sub       | 完全相容                                         | 無需處理                                  |
| Client libraries                       | 完全相容（透過 redis_version 協商）              | 無需改 code                               |
| Cluster / Sentinel                     | 完全相容（同 Redis 模型）                        | 無需處理                                  |
| Redis 7.4+ 新功能（fork 後新增）       | Valkey 不一定跟進                                | 盤點是否用到、確認 Valkey 對應            |
| Redis Stack 商業 module（JSON/Search） | 不相容（Valkey 有 valkey-search / valkey-bloom） | 盤點 module 使用、確認替代或改寫          |
| RedisInsight 等 Redis Inc 監控工具     | 部分 vendor-specific 命令缺                      | 改通用工具（valkey-cli / redis_exporter） |

**audit 的關鍵 output**：兩份清單——(1) 用到的 Redis 7.4+ 功能（fork 後新增、Valkey 可能沒有）、(2) 載入的 Redis Stack module。這兩塊是僅有的相容風險，其餘資料層零工作。盤點方法：

```bash
# 盤點載入的 module（最大相容風險）
redis-cli MODULE LIST

# 盤點是否用到 7.4+ 功能（抓 production traffic 對照 Redis 7.4 changelog）
redis-cli MONITOR    # 限時抓樣、grep 可疑的新命令
```

## Step-by-step cutover

因為 RDB 檔案相容，cutover 比 DragonflyDB 更簡單（無版本轉換風險）：

```bash
# 1. 部署 Valkey（同 Redis 配置、可直接沿用 redis.conf）
docker run -d --name valkey -p 6380:6379 \
  -v /data/valkey:/data \
  valkey/valkey:8 valkey-server /etc/valkey/valkey.conf

# 2. Redis 端 BGSAVE 產生 RDB
redis-cli -h redis-primary BGSAVE
redis-cli -h redis-primary INFO Persistence | grep rdb_last_save_time

# 3. 把 dump.rdb 拷給 Valkey（檔案格式相容、無需轉換）
scp redis-primary:/var/lib/redis/dump.rdb valkey-host:/data/valkey/

# 4. 重啟 Valkey 載入 RDB
docker restart valkey

# 5. 驗證資料一致 + 版本
valkey-cli -h valkey-host -p 6380 DBSIZE          # 對齊 Redis DBSIZE
valkey-cli -h valkey-host -p 6380 INFO server | grep redis_version  # 7.2.4

# 6. 替代方案（零停機）：用 replicaof 讓 Valkey 當 Redis 的 replica、即時同步後 promote
#    valkey-cli -h valkey-host REPLICAOF redis-primary 6379
#    重要邊界：此路徑只在 source 是 Redis 7.2 或更早版本時成立。
#    Redis 7.4+（Community Edition）改了複製格式、Valkey 無法當其 replica
#    → source 為 7.4+ 時改走上面的 RDB 拷貝路徑（步驟 2-4）。

# 7. Cutover：client 配置切到 Valkey endpoint、Redis 留 standby
```

關鍵時間點：

- **RDB 拷貝 + load**：100GB 約 5-15 分鐘（無版本轉換、比 DragonflyDB 少一道風險）
- **replicaof 路徑**：要零停機可讓 Valkey 當 Redis replica 即時同步、確認 lag 趨零後 promote + 切 client（僅限 source 為 Redis 7.2 或更早；7.4+ 複製格式已分歧、不適用、改走 RDB 拷貝）
- **Cutover**：client 配置切換（單次完成、硬邊界）、Redis 留 standby 1-2 週
- **Decom**：無相容問題後關閉 Redis

## Production 故障演練

### Case 1：用到 Redis 7.4+ 功能、Valkey 沒有

**徵兆**：cutover 後某功能報 `unknown command` 或行為不同，命令是 Redis 在 7.4 之後（fork 點之後）才加的。

**根因**：Valkey fork 自 Redis 7.2.4，Redis 7.4+ 新增的功能 Valkey 不一定跟進。pre-migration audit 漏掉了這些 fork 後的新功能。

**修法**：

1. pre-migration 對照 Redis 7.4+ changelog 盤點用到的新功能（audit 清單第一項）
2. Valkey 有對應就確認版本、沒有就評估改寫或留在 Redis 商業版
3. 多數標準 cache 用法不碰 7.4+ 新功能，這個風險集中在用了較新進階功能的部署
4. Valkey 自己的 roadmap（valkey.io）會逐步補上 Redis 新功能，可追蹤

### Case 2：載入了 Redis Stack 商業 module

**徵兆**：cutover 後 `JSON.SET` / `FT.SEARCH` 報 `unknown command`，application 部分功能失效。

**根因**：用了 Redis Stack 的商業 module（RedisJSON / RedisSearch），這些不在 fork 範圍。Valkey 有自己的 valkey-search / valkey-bloom，但不是同一套命令、要另外安裝。

**修法**：

1. pre-migration `MODULE LIST` 盤點所有載入的 module（audit 清單第二項）
2. 確認 Valkey 對應替代（valkey-search 對 RedisSearch）、確認命令相容度
3. 沒有對應的評估改 module-free 設計（JSON 操作拉回 application 層）或留在 Redis Inc 商業版
4. 對應 [Valkey 相容性 deep article](/backend/02-cache-redis/vendors/valkey/redis-compatibility-and-io-threads/) 的三層相容邊界

### Case 3：以為換 Valkey 解決了記憶體 / fork 問題

**徵兆**：因為 Redis 的 OOM 或 fork 延遲尖峰而遷 Valkey，遷完發現同樣問題還在。

**根因**：Valkey fork 自 Redis 7.2.4，繼承了完全相同的記憶體模型、eviction 演算法、AOF/RDB fork 機制。這些行為在 Valkey 上一模一樣——遷移沒有改變它們。

**修法**：

1. 記憶體 / fork 調校在 Valkey 上跟 Redis 完全相同，直接套用 [Redis 記憶體調校](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/) 與 [persistence / fork latency](/backend/02-cache-redis/vendors/redis/persistence-fork-latency/)
2. 遷 Valkey 的理由應是授權合規 / 多執行緒吞吐 / managed 成本，不是記憶體問題
3. fork 尖峰要根治走 [DragonflyDB](/backend/02-cache-redis/vendors/dragonflydb/) 的 fork-less，不是換 Valkey
4. 遷移前釐清痛點是授權（Valkey 解）還是架構（Valkey 不解）

### Case 4：授權合規驗證沒做完整、合規卡關

**徵兆**：技術遷移完成、但法務 / 合規 review 要求證明「不再使用 RSALv2 / SSPL 授權的軟體」，缺少證據。

**根因**：這個遷移的 driver 是授權合規，但團隊只做了技術 cutover、沒收集合規證據。Redis 的 binary / image / 相依套件若還殘留在某些環境，合規目標沒真正達成。

**修法**：

1. 盤點所有環境（dev / staging / prod / CI）的 Redis binary / image / 相依，確認全部換成 Valkey
2. 收集合規證據：image SBOM、套件清單、部署 manifest 顯示 Valkey BSD 授權
3. 把「不再使用非 OSI 授權 cache」寫成可驗證的 CI 檢查（掃 image / 依賴）
4. 依 [migration 方法論](/posts/migration-playbook-methodology/) 的合規驅動漏類，audit 重點就是 evidence collection

### Case 5：監控 dashboard 部分指標斷掉

**徵兆**：cutover 後 RedisInsight 或某監控 dashboard 部分面板空白、vendor-specific 命令回錯。

**根因**：RedisInsight 等 Redis Inc 工具有部分偏商業版的命令，Valkey 不一定實作。核心指標通用，但進階面板可能缺。

**修法**：

1. 監控改用通用工具：valkey-cli INFO、Prometheus + redis_exporter（相容 Valkey）、Grafana
2. 核心指標（used_memory / keyspace_hits / connected_clients）在 Valkey 完全相容、覆蓋不受影響
3. 把監控相容性納入 cutover 前驗證、不要遷完才發現面板空白
4. RedisInsight 連 Valkey 多數仍可用、只是部分 vendor 進階面板缺

## Capacity / cost 對照

| 維度               | Redis（self-managed）           | Valkey（self-managed）                          | 取捨                                       |
| ------------------ | ------------------------------- | ----------------------------------------------- | ------------------------------------------ |
| 授權               | RSALv2 / SSPL（非 OSI）         | BSD 3-clause（OSI、Linux Foundation）           | Valkey 對合規敏感場景是決定性優勢          |
| 核心效能           | baseline                        | 同 Redis 7.2.4 + 8.x 多執行緒選項               | Valkey 多核 workload 可更高（依 workload） |
| 相容度             | 原生                            | 100%（fork、檔案相容）                          | 平手（同源）                               |
| 記憶體 / fork      | baseline                        | 完全相同（同源）                                | 平手（遷移不改變這層）                     |
| 7.4+ 新功能        | 有                              | 不一定跟進                                      | Redis 領先（用到才在意）                   |
| Redis Stack module | RedisJSON / Search / Graph      | valkey-search / valkey-bloom（不同套）          | Redis 商業 module 較全                     |
| managed 選項       | ElastiCache for Redis（legacy） | ElastiCache for Valkey（AWS default、約低 20%） | Valkey 在 AWS 生態成本優勢                 |
| 遷移成本           | —                               | 極低（drop-in + 檔案相容）                      | Valkey 是最容易的遷移目標                  |

**判讀**：合規敏感（公部門 / 企業 OSI 政策）或想降 managed 成本 → 遷 Valkey（drop-in、風險集中在 module / 7.4+ 盤點）；重度依賴 Redis Stack 商業 module → 留 Redis Inc 商業版。

## 整合 / 下一步

### 跟 [ElastiCache for Valkey](/backend/02-cache-redis/vendors/aws-elasticache/) 對位

AWS 已把 ElastiCache default engine 設為 Valkey（約低 Redis 20%）。自管 Redis → ElastiCache for Valkey 是「換授權 + 轉 managed」一次到位，但要同時處理 [managed 責任邊界](/backend/02-cache-redis/vendors/aws-elasticache/managed-responsibility-boundary/)（failover / cluster mode / client 重連）。

### 跟 client / 監控整合

client library 零改（透過 redis_version 協商）；監控把 exporter 指向 Valkey 即可（redis_exporter 相容）、RedisInsight 部分面板需換通用工具。

### 跟 Valkey 8 多執行緒對位

遷移後可評估開 Valkey 8 的 io-threads 榨多核吞吐（Redis 7.2.4 沒有的能力），見 [Valkey 相容性與 io-threads deep article](/backend/02-cache-redis/vendors/valkey/redis-compatibility-and-io-threads/)。

### 下一步議題

- **反向遷移**（Valkey → Redis）：僅在重度依賴 Redis 7.4+ 功能或 Stack 商業 module 時需要、同樣 drop-in
- **跨雲 managed Valkey**：GCP Memorystore / Azure Cache 的 Valkey 支援陸續推出、評估 vendor boundary
- **授權合規 CI 化**：把「不使用非 OSI 授權 cache」寫成持續檢查

## 相關連結

- Source vendor：[Redis](/backend/02-cache-redis/vendors/redis/)
- Target vendor：[Valkey](/backend/02-cache-redis/vendors/valkey/)
- 平行 migration playbook：[Redis → DragonflyDB](/backend/02-cache-redis/vendors/redis/migrate-to-dragonflydb/)（重寫型 drop-in）、[Redis → Memcached](/backend/02-cache-redis/vendors/redis/migrate-to-memcached/)
- Methodology：[Migration playbook methodology](/posts/migration-playbook-methodology/)（Type B drop-in + 合規驅動漏類）
