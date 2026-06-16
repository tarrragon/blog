---
title: "Momento"
date: 2026-06-16
description: "Serverless cache、按用量計費、無容量規劃"
weight: 7
tags: ["backend", "cache", "vendor"]
---

Momento 是 serverless cache 服務、承擔三個責任：把 cache 變成一個按用量計費的 API（沒有 node、沒有 cluster、不規劃容量）、自動隨流量 scale（尖峰自動擴、閒置不付固定費）、提供原生 SDK 與 Redis / Memcached 相容介面（既有 client 可遷）。設計取捨偏向「把 cache 的容量規劃與維運完全消除、用計費換掉 sizing」、是不想養 cache 叢集又要彈性的選項。

對「流量不可預測、不想規劃容量與 sizing、團隊沒有 cache 運維資源」這條路徑、Momento 是 serverless 方向的代表。它跟自管 Redis、managed cache 的上層取捨（自管 vs managed vs serverless vs BaaS bundle）見 [0.22 能力級買 vs 建](/backend/00-service-selection/capability-buy-vs-build/)。

> 本頁的計費、limit 與功能宣稱以 [Momento 官方文件](https://docs.momentohq.com/) 與 [Momento 定價](https://www.gomomento.com/pricing/) 為準、最後檢查日 2026-06-16。Momento 是 SaaS、需帳號與 API key、無法本機 docker 驗證、指令為依官方文件的範例。

## 本章目標

讀完本章後、你應該能：

1. 理解 serverless cache 跟 node-based / managed cache 的計費與維運差異
2. 評估按用量計費（per request + data transfer）對你的流量形狀划不划算
3. 判斷 Momento 原生 SDK vs Redis 相容介面的遷移路徑
4. 區分 Momento 跟 ElastiCache Serverless 的定位差異
5. 判斷哪些 cache 場景適合 serverless、哪些該回 node-based

## 最短路徑：用 SDK 連 Momento

```text
# 1. 在 Momento Console 建 cache + 取得 API key（無 node / cluster 配置）
# 2. 用語言 SDK（以 pseudo-code 示意、實際 API 以官方 SDK 文件為準）

client = CacheClient(api_key, default_ttl=60s)
client.set("my-cache", "foo", "bar")     # 寫入、TTL 內有效
client.get("my-cache", "foo")            # → "bar"
```

最短路徑的重點是「沒有 endpoint / node / sizing 要配」——建 cache 是一個 API 動作、不是 provision 一台機器。實際 SDK 介面以 [Momento SDK 文件](https://docs.momentohq.com/) 為準。

## 日常操作與決策形狀

### SDK 與相容介面

子議題：

- 原生 SDK（多語言）：gRPC-based、Momento 自有 API
- Redis / Memcached 相容介面：既有 Redis / Memcached client 可遷（相容範圍以官方為準、要驗證）
- 沒有 redis-cli 等價的 server 操作（serverless 無 server 可登入）

### 計費模型（核心決策）

子議題：

- 按用量計費：data transfer（傳輸量）+ 可能的 request / storage 維度（以官方定價為準）
- 無固定 node 費用：閒置時段不付 idle node 的錢
- 流量尖峰自動 scale：不需預留容量、但尖峰量直接反映在帳單

### 沒有容量規劃

子議題：

- 不選 node type、不設 maxmemory、不規劃 shard
- scaling 由 Momento 處理、application 端不感知
- 代價：失去對底層的控制（無法調 eviction policy 等 server 參數）

## 進階主題（按需閱讀）

### Serverless 計費的甜蜜點與陷阱

子議題：

- 甜蜜點：流量不可預測、有大量閒置時段、不想為峰值預留容量
- 陷阱：穩態高流量下、按用量可能比 node-based + Reserved Instance 貴
- 跟 [ElastiCache Serverless 的計費踩坑](/backend/02-cache-redis/vendors/aws-elasticache/managed-responsibility-boundary/) 同類議題、access pattern 低效會推高帳單

### Momento vs ElastiCache Serverless

子議題：

- Momento：cache-as-API、完全 serverless、跨雲（不綁單一 cloud）
- ElastiCache Serverless：AWS 生態內的 node 抽象、仍是 ElastiCache engine、綁 AWS
- 選擇：要完全擺脫容量規劃 + 跨雲 → Momento；已在 AWS 生態 + 要 engine 控制 → ElastiCache

### 遷移與相容性驗證

子議題：

- 從 Redis / Memcached 遷 Momento：用相容介面或改用原生 SDK
- 相容範圍要逐項驗證（serverless 不支援 server-side 操作如 SCAN 全庫、Lua 等、以官方為準）
- 失去的能力：server 參數調校、自管 persistence、module

## 排錯快速判讀

### 帳單超出預期

操作原則：serverless 帳單反映實際用量、先看 data transfer 與 request 量。判讀：access pattern 低效（大量小請求、大 value）會推高、用批次 / 合併降量；穩態高流量重新評估 node-based。

### 延遲比自管高

操作原則：serverless cache 多一層 API gateway / 跨網路、延遲可能高於同 VPC 的自管 Redis。判讀：latency-sensitive 且穩態高流量的場景、評估自管或 managed node-based。

### 相容介面行為差異

操作原則：Redis 相容介面不等於 100% Redis、server-side 操作可能不支援。判讀：對照官方相容清單、用到的命令逐一驗證。

## 何時改走其他服務

| 需求形狀                         | 改走                                                                                    |
| -------------------------------- | --------------------------------------------------------------------------------------- |
| 穩態高流量、成本敏感             | node-based [Redis / Valkey](/backend/02-cache-redis/vendors/redis/) + Reserved Instance |
| 需要 server 參數 / eviction 控制 | 自管 Redis / [ElastiCache](/backend/02-cache-redis/vendors/aws-elasticache/)            |
| 已在 AWS 生態                    | [ElastiCache Serverless](/backend/02-cache-redis/vendors/aws-elasticache/)（同生態）    |
| 需要 Redis data types / module   | [Redis](/backend/02-cache-redis/vendors/redis/)（完整 data types）                      |
| process-local 極低延遲           | [Caffeine](/backend/02-cache-redis/vendors/caffeine/)（JVM 內、無網路）                 |

## 不在本頁內的主題

- Momento 完整 SDK API（各語言、以官方文件為準）
- 詳細計費計算（以官方定價為準）
- Redis / Memcached 相容介面的完整相容矩陣
- Momento Topics（pub/sub）等 cache 以外的產品線

## 案例回寫

### 跨 vendor 對照（本模組 case 庫暫無 Momento-specific case）

Momento 是較新的 serverless cache、本 blog 的 cache case 庫（Meta / Shopify / Netflix / Cloudflare / Tinder / Tubi / Snap）暫無 Momento production case。以下用 serverless 的角度對照既有 case 提供判讀。

| 案例                                                                                                  | 對 Momento 的對應                                                            |
| ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| [2.C9 Cache Stampede](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/)       | serverless 也會 stampede、client-side jitter / singleflight 仍要自己做       |
| [9.C25 Tubi feature store](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/) | 「feature 可重算才選 cache」的判斷對 serverless 一樣適用、不可重建走 durable |
| [2.C10 規模對照](/backend/02-cache-redis/cases/contrast-cache-strategy-by-scale/)                     | serverless 適合早期 / 不可預測流量、規模穩定後評估 node-based 成本           |

**待補 Momento-specific 案例**：serverless cache 的成本與彈性 production 個案、從 ElastiCache 遷 Momento 的成本對照、不可預測流量場景的採用分享。

## 下一步路由

- 上游能力：[0.22 能力級買 vs 建](/backend/00-service-selection/capability-buy-vs-build/)（自管 vs managed vs serverless）、[0.6 成本取捨](/backend/00-service-selection/cost-risk-tradeoffs/)
- 平行 vendor：[AWS ElastiCache](/backend/02-cache-redis/vendors/aws-elasticache/)（Serverless 選項）、[Caffeine](/backend/02-cache-redis/vendors/caffeine/)（另一端：process-local）
- 上游概念：[2.2 Cache Aside](/backend/02-cache-redis/cache-aside/)
