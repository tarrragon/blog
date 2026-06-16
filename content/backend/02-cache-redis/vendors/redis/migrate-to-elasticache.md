---
title: "自管 Redis / Valkey → AWS ElastiCache：engine 不變、變的是誰運維"
date: 2026-06-16
description: "自管 Redis/Valkey 遷到 ElastiCache 的特殊之處：engine 沒變（Redis 還是 Redis）、data model 沒變、API 沒變——變的只有運維責任歸屬。本文跑 6 維 diff audit 對映 Type C operational hybrid、展開 VPC/安全/cutover 的實際工作、以及『把 failover/patching 交出去、同時交出哪些控制權』的責任邊界，5 個 production 踩坑"
weight: 22
tags: ["backend", "cache", "redis", "aws-elasticache", "migration", "managed", "type-c"]
---

> 本文是跨 vendor migration playbook、cross-link [Redis](/backend/02-cache-redis/vendors/redis/) / [Valkey](/backend/02-cache-redis/vendors/valkey/)（source、自管）跟 [AWS ElastiCache](/backend/02-cache-redis/vendors/aws-elasticache/)（target、managed）。跑 [migration-playbook-methodology 6 維 audit](/posts/migration-playbook-methodology/) 對映 **Operational model = High（自管 → managed）、其他 Low → Type C operational hybrid**。ElastiCache 是 managed SaaS、AWS 操作依官方文件（未本機驗證、引數以官方為準）、最後檢查日 2026-06-16。

## engine 不變、變的是誰運維

多數 vendor 遷移會換掉某個本質的東西——協定、data model、paradigm。自管 Redis/Valkey → ElastiCache 一個都沒換：ElastiCache 跑的就是 Redis 或 Valkey engine，同樣的 RESP 協定、同樣的 data types、同樣的 client library、同樣的命令。application code 幾乎不用動。

那遷的是什麼？**運維責任的歸屬**。自管時你自己部署、自己打 patch、自己設 replication、自己半夜起來處理 failover。ElastiCache 把這些接走——AWS 做 failover、patching、snapshot、跨 AZ 複製。這個遷移的全部工作量集中在「把運維交出去」這件事上：網路（VPC）、安全（IAM / Security Group）、cutover 的資料連續性，以及想清楚**交出運維的同時、交出了哪些控制權**（你不能再 SSH 進去、不能改任意 config、parameter group 限定可調項）。

這對映 [migration 方法論](/posts/migration-playbook-methodology/) 的 Type C operational hybrid——operational model 是唯一的 High 維度，其他全 Low。本文展開這個「engine 不變、運維轉移」遷移的實際工作與責任邊界。

## 6 維 diff dimension audit

| 維度                   | 評估                                              | 等級     |
| ---------------------- | ------------------------------------------------- | -------- |
| Schema / API           | 同 engine（Redis/Valkey）、RESP 一致、命令一致    | Low      |
| **Operational model**  | **自管 → AWS managed（failover/patch/snapshot）** | **High** |
| Abstraction / paradigm | 完全相同（同 engine）                             | Low      |
| Number of components   | 1 → 1                                             | Low      |
| Application change     | endpoint 換、client 加 reconnect / TLS、其餘不動  | Low      |
| Data topology          | cache 可重建（re-warm）或 RDB seed / online 複製  | Low      |

唯一 High 是 operational model，對映 **Type C operational hybrid**。Type C 的結構是「operational audit 前置 + drop-in cutover」——因為 engine/API 不變，cutover 本身接近 drop-in（換 endpoint），重點在前置的網路/安全/責任邊界盤點。

## operational audit：cutover 前要盤點的

ElastiCache 把運維接走，但也劃下新的邊界。cutover 前必盤：

| 面向         | 自管時你做的             | ElastiCache 後                                        |
| ------------ | ------------------------ | ----------------------------------------------------- |
| 部署 / patch | 自己裝、自己升級         | AWS 管（你失去任意版本控制、跟 AWS 的 engine 版本走） |
| failover     | 自己設 Sentinel / 手動切 | Multi-AZ 自動（你要確保 client 會重連）               |
| config       | 改任意 redis.conf        | 只能改 parameter group 開放的項（部分鎖死）           |
| 網路存取     | 自己的網路               | 只在 VPC 內可達、要設 subnet group / Security Group   |
| 認證         | AUTH password / 自管 TLS | IAM auth（Redis 7+）/ ElastiCache 管的 TLS            |
| 監控         | 自己的 Prometheus 等     | CloudWatch（指標名與自管不同、dashboard 要改）        |

**audit 的關鍵 output**：(1) 你目前改了哪些 redis.conf 項、ElastiCache parameter group 是否支援；(2) client 是否有 failover reconnect 邏輯（managed failover 不會幫你重連）；(3) 監控要從自管工具搬到 CloudWatch。這三項是 Type C 的核心工作。詳細的 managed 責任邊界見 [ElastiCache 責任邊界 deep article](/backend/02-cache-redis/vendors/aws-elasticache/managed-responsibility-boundary/)。

## cutover：資料連續性的兩條路

因為 engine/API 不變，cutover 接近 drop-in（換 endpoint）。資料連續性有兩條路：

```text
路徑 A：re-warm（cache 可重建、最簡單）
  1. 建 ElastiCache cluster（空的、選 Valkey / Redis engine、設 parameter group）
  2. application 雙寫（自管 + ElastiCache）、讀仍走自管
  3. 讀切到 ElastiCache endpoint、cache miss 回源 warm up
  4. 命中率追上 → 停寫自管 → 下線自管

路徑 B：RDB seed（要 cache 連續性、避免 warm-up origin 衝擊）
  1. 自管端 BGSAVE 產生 RDB
  2. RDB 上傳 S3、ElastiCache 從 S3 seed 建 cluster（依官方 restore 流程）
  3. application 換 endpoint cutover
  （ElastiCache 也提供 self-managed Redis online migration、見官方文件）
```

判讀：

- 純 cache、能接受短暫 warm-up → 路徑 A（最簡單、無資料遷移）
- 大 dataset、warm-up 會打爆 origin → 路徑 B（RDB seed 保連續性）
- AWS CLI 建 cluster 與 restore 細節依 [ElastiCache 官方文件](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/)（未本機驗證）
- engine 選 Valkey（AWS default、約低 Redis 20%）除非有 Redis 商業 module 依賴

## Production 故障演練

### Case 1：parameter group 不支援自管時改的 config

**徵兆**：自管時改了某個 redis.conf 項（例如特定 `client-output-buffer-limit` 或某個進階參數），遷到 ElastiCache 後該設定無法套用或行為不同。

**根因**：ElastiCache 只允許改 parameter group 開放的項，部分 config 被 AWS 鎖死（為了 managed 穩定性）。自管時的任意 config 自由度在 managed 後收窄。

**修法**：

1. pre-migration 列出自管端所有非預設 config，逐項對照 ElastiCache parameter group 支援度
2. 不支援的項要評估影響——有些是 AWS 已用更好的方式處理、有些要調整 application 適應
3. 把這個盤點放在 operational audit（cutover 前），不要遷完才發現
4. 高度依賴特殊 config 調校的場景，managed 可能不適合、留自管

### Case 2：failover 後 client 不重連（managed 不幫你重連）

**徵兆**：ElastiCache Multi-AZ failover 完成，但 application 持續連舊 primary、寫入失敗。

**根因**：ElastiCache 接走了 failover（自動晉升 replica），但 application 的 client 重連仍是你的責任——這是 [managed 責任邊界](/backend/02-cache-redis/vendors/aws-elasticache/managed-responsibility-boundary/) 的核心：AWS 換 primary，client 要自己跟上。

**修法**：

1. client 連 primary endpoint（會跟著 failover 更新 DNS）、不寫死 node IP
2. client 設合理 socket timeout + retry + 縮短 DNS 快取
3. 遷移前就驗證 client 有 failover reconnect 行為（自管 Sentinel 時可能靠不同機制）
4. 對應 [Redis Sentinel failover 時序](/backend/02-cache-redis/vendors/redis/sentinel-ha-failover/)：自管與 managed 的 failover 機制不同、client 處理要重驗

### Case 3：endpoint 只在 VPC 內、cutover 後連不上

**徵兆**：cutover 後 application 完全連不上 ElastiCache、連線逾時。

**根因**：ElastiCache endpoint 只在 VPC 內可達、不對公網開放。Security Group 沒開 6379、subnet group 配置錯、或 application 不在同 VPC / 沒有 VPC peering，就連不上。

**修法**：

1. cutover 前確認 Security Group 開 6379 給 application 的來源、subnet group 正確
2. application 不在同 VPC 要設 peering / Transit Gateway
3. 從 VPC 內 EC2 先 `redis-cli -h <endpoint> ping` 驗證連通，再切 application
4. 這是自管（自己的網路）→ managed（AWS VPC 模型）最常見的卡點

### Case 4：監控斷層（自管工具 → CloudWatch）

**徵兆**：cutover 後原本的 Prometheus / Grafana dashboard 全空、告警失效。

**根因**：自管時用 redis_exporter + Prometheus，ElastiCache 的指標在 CloudWatch、指標名與維度不同。直接搬 dashboard 不會動。

**修法**：

1. cutover 前把關鍵告警在 CloudWatch 重建（`DatabaseMemoryUsagePercentage` / `ReplicationLag` / `CurrConnections` 等）
2. 要保留 Grafana 可用 CloudWatch data source 接
3. 把監控遷移納入 operational audit、不要遷完才發現沒監控
4. 核心指標語意相同（記憶體 / 命中 / 連線 / 複製延遲）、只是來源與命名變了

### Case 5：以為 managed 就不會 OOM / stampede / 熱 key

**徵兆**：遷到 ElastiCache 後仍然 OOM、cache stampede、熱 key 打爆單 shard。

**根因**：ElastiCache 接走的是運維（failover/patch/snapshot），不是 cache 使用方式的問題。記憶體淘汰、stampede、熱 key、key 設計仍是你的責任——managed 不等於 hands-off。

**修法**：

1. 記憶體 / eviction 調校仍要做（透過 parameter group 設 maxmemory-policy），見 [記憶體調校](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/)
2. stampede / 熱 key 的 application 端防護（jitter / singleflight / 兩層 cache）照舊
3. 釐清 managed 的責任邊界——左欄 AWS 管、右欄你管，見 [責任邊界 deep article](/backend/02-cache-redis/vendors/aws-elasticache/managed-responsibility-boundary/)
4. 遷 managed 是減運維、不是免設計

## Capacity / cost 對照

| 維度          | 自管 Redis / Valkey             | ElastiCache（managed）              |
| ------------- | ------------------------------- | ----------------------------------- |
| engine / API  | 同（Redis / Valkey）            | 同（Redis / Valkey engine）         |
| 運維責任      | 全部自己扛                      | failover / patch / snapshot 交 AWS  |
| config 自由度 | 任意 redis.conf                 | parameter group 開放項（部分鎖死）  |
| failover      | 自設 Sentinel / Cluster         | Multi-AZ 自動（client 要會重連）    |
| 成本          | 機器 + 人力運維                 | node 費 + managed premium（省人力） |
| 控制權        | 完全                            | 受 AWS 邊界限制                     |
| 適合          | 要極致控制 / 跨雲 / 特殊 config | AWS 生態 / 要減運維 / 可預測 SLA    |

**判讀**：在 AWS 生態、要把運維交出去、能接受 config 自由度收窄 → 遷 ElastiCache（engine 不變、Type C 低風險）；要極致控制 / 跨雲 / 依賴特殊 config → 留自管。engine 選 Valkey 省約 20%。

## 整合 / 下一步

self-managed → ElastiCache 是運維轉移，它跟 managed 邊界與 engine 調校交織：

- **跟 [ElastiCache 責任邊界 deep article](/backend/02-cache-redis/vendors/aws-elasticache/managed-responsibility-boundary/)**：遷過去後哪些 AWS 管、哪些仍你管，是這個遷移的核心後果。
- **跟 [Redis Sentinel failover](/backend/02-cache-redis/vendors/redis/sentinel-ha-failover/)**：自管 failover（Sentinel）→ managed failover（Multi-AZ），client 重連邏輯要重驗。
- **跟 [Valkey](/backend/02-cache-redis/vendors/valkey/)**：ElastiCache default engine 是 Valkey，自管 Redis 遷 ElastiCache for Valkey 是「換授權 + 轉 managed」一次到位（見 [Redis → Valkey 遷移](/backend/02-cache-redis/vendors/redis/migrate-to-valkey/)）。
- **跟 0.22 能力級買 vs 建**：自管 vs managed 的上層取捨見 [能力級買 vs 建](/backend/00-service-selection/capability-buy-vs-build/)，本文是「決定買（managed）之後」的遷移執行。

## 相關連結

- Source vendor：[Redis](/backend/02-cache-redis/vendors/redis/) / [Valkey](/backend/02-cache-redis/vendors/valkey/)（自管）
- Target vendor：[AWS ElastiCache](/backend/02-cache-redis/vendors/aws-elasticache/)
- 對應 deep article：[ElastiCache 責任邊界](/backend/02-cache-redis/vendors/aws-elasticache/managed-responsibility-boundary/)
- 相關 migration：[Redis → Valkey](/backend/02-cache-redis/vendors/redis/migrate-to-valkey/)（換授權 + 可同時轉 managed）
- Methodology：[Migration playbook methodology](/posts/migration-playbook-methodology/)（Type C operational hybrid）
