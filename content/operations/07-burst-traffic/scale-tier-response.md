---
title: "規模分級應對表"
date: 2026-06-20
description: "自用級 → 中型 → 大型 → 商業網站級的四級應對方案 — 每級的觸發條件、架構組成和成本"
weight: 4
tags: ["devops", "burst-traffic", "scaling", "architecture", "tier"]
---

突發流量的應對方案隨服務規模分成四級。每一級在前一級的基礎上增加元件，複雜度和成本同步上升。選擇哪一級取決於「預期的峰值流量」和「可接受的降級程度」。

## 四級分級

### Tier 1：自用級（< 100 events/sec）

```text
SDK ──→ Collector (單 binary + SQLite)
```

| 維度     | 設定                               |
| -------- | ---------------------------------- |
| 架構     | 單 Go binary、SQLite embedded      |
| 流量控制 | 背壓（channel buffer 10000 + 429） |
| 突發應對 | SDK 離線 buffer 吸收短暫 burst     |
| 降級     | 無（流量不會到需要降級的程度）     |
| 成本     | 零（自有主機、零外部依賴）         |
| 適用     | 自用工具、開發期測試、小型團隊     |

Tier 1 的假設是峰值流量不超過 SQLite WAL mode 的寫入能力（每秒數千筆）。自用場景下這個假設幾乎永遠成立。

### Tier 2：中型（100-10000 events/sec）

```text
         ┌─ Collector A ──→ PostgreSQL
SDK ──→ LB ─┤
         └─ Collector B ──→ PostgreSQL
```

| 維度     | 設定                                                        |
| -------- | ----------------------------------------------------------- |
| 架構     | 多 collector + load balancer + PostgreSQL                   |
| 流量控制 | 背壓 + per-SDK rate limit                                   |
| 突發應對 | LB 分散流量 + collector 水平擴展                            |
| 降級     | 動態取樣（超載時 SDK 降到 10%）                             |
| 成本     | PostgreSQL + LB 的維護（可用 managed service 降低維護成本） |
| 適用     | 使用者數百到數千、有付費能力                                |

Tier 1 → Tier 2 的觸發：SQLite 的 `database is locked` 頻繁出現，或 dashboard 的聚合查詢需要 PostgreSQL 的能力。

### Tier 3：大型（10000-100000 events/sec）

```text
         ┌─ Collector A ─┐
SDK ──→ LB ─┤               ├─→ Queue ──→ Worker 群 ──→ PostgreSQL
         └─ Collector B ─┘
```

| 維度     | 設定                                                         |
| -------- | ------------------------------------------------------------ |
| 架構     | Collector 群 + queue（NATS / Kafka）+ worker 群 + PostgreSQL |
| 流量控制 | 背壓 + rate limit + bulkhead                                 |
| 突發應對 | Queue 做時間緩衝（積壓 → 追趕）                              |
| 降級     | 動態取樣 + 事件優先級 + 功能降級                             |
| 成本     | Queue + worker 的基礎設施（顯著上升）                        |
| 適用     | 中大型 SaaS、使用者數萬                                      |

Tier 2 → Tier 3 的觸發：直接寫 PostgreSQL 的背壓頻繁觸發（即使有多個 collector 寫入）。

### Tier 4：商業網站級（> 100000 events/sec）

```text
SDK ──→ CDN/Edge ──→ LB ──→ Collector 群 ──→ Kafka ──→ Worker 群 ──→ 分層 DB
                                                                      ├─ 即時查詢 DB（ClickHouse / TimescaleDB）
                                                                      └─ 歸檔 DB（S3 + Athena）
```

| 維度     | 設定                                            |
| -------- | ----------------------------------------------- |
| 架構     | CDN edge 收集 + Kafka + 分層存儲                |
| 流量控制 | CDN rate limit + 全鏈路背壓                     |
| 突發應對 | Kafka partition 水平擴展 + auto-scaling worker  |
| 降級     | 全套（動態取樣 + 優先級 + 聚合前移 + 功能降級） |
| 成本     | 基礎設施團隊級別的投入                          |
| 適用     | 大型 SaaS、電商、社群平台                       |

Tier 3 → Tier 4 的觸發：Kafka 單 cluster 的吞吐不夠、或查詢需要跨日誌級的時間序列分析。

多數自架開源工具不需要超過 Tier 2。Tier 3 和 Tier 4 是商業 SaaS 的領域。

## 規模遷移路徑

| 遷移       | 改什麼                                                | 停機                                   |
| ---------- | ----------------------------------------------------- | -------------------------------------- |
| Tier 1 → 2 | Storage backend 切 PostgreSQL + 加 LB + 加 collector  | config change + 資料遷移（分鐘級停機） |
| Tier 2 → 3 | 加 queue + 改 collector 為 ingestion-only + 加 worker | 架構重構（需要開發時間）               |
| Tier 3 → 4 | 加 CDN edge + 分層 DB + auto-scaling                  | 基礎設施工程（需要專職團隊）           |

每一級的遷移成本遞增。Tier 1 → 2 是 config change 級、Tier 2 → 3 是架構重構級、Tier 3 → 4 是團隊級。選擇起始 tier 時選最低的足夠 tier — 過早引入高 tier 的複雜度是浪費。

## 下一步路由

- 流量管控的四種機制 → [模組三 流量管控](/operations/03-traffic-management/)
- 容量預備和壓力測試 → [模組五 容量規劃](/operations/05-capacity-planning/)
- Collector 的可插拔 storage 架構 → [monitoring 模組四 規模演進](/monitoring/04-collector/scaling-evolution/)
- Queue 的選型 → [backend 非同步佇列](/backend/03-message-queue/)
