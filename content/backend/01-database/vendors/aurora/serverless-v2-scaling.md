---
title: "Aurora Serverless v2 適用判斷：ACU 自動擴縮、混合 cluster 與何時不該用"
date: 2026-06-02
description: "Aurora Serverless v2 不是「比較便宜的 Aurora」；本文展開 ACU 計費粒度、秒級自動擴縮機制、min/max ACU 設定、serverless 與 provisioned 同 cluster 混用，以及穩定高負載下 serverless 反而更貴的成本 crossover 邊界"
weight: 31
tags: ["backend", "database", "aurora", "serverless", "capacity", "cost", "deep-article"]
---

Aurora Serverless v2 把 instance 的容量從「開機時固定的 instance class」改成「按負載秒級伸縮的 ACU」。它解的問題很具體：固定 provisioned cluster 在離峰時段付滿整台機器的錢、卻只用一小部分；尖峰來時又被 instance class 上限卡住。但 serverless v2 不是「比較便宜的 Aurora」——穩定高負載下它反而比同等 provisioned 貴。要不要用，取決於 workload 的負載形狀是否間歇、是否難預測。

本文不是 Aurora overview（請看 [Aurora vendor 頁](/backend/01-database/vendors/aurora/)）— 而是 Serverless v2 的容量機制、設定與適用邊界的實作層教學。

## 核心機制：ACU 與秒級擴縮

Serverless v2 的容量單位是 ACU（Aurora Capacity Unit），一個 ACU 對應一組固定比例的記憶體與運算資源。cluster 不再綁定一個 instance class，而是設一個 ACU 區間（min / max），Aurora 依即時負載在區間內伸縮：

| 屬性     | Provisioned                             | Serverless v2            |
| -------- | --------------------------------------- | ------------------------ |
| 容量設定 | 固定 instance class（如 db.r6g.xlarge） | min / max ACU 區間       |
| 計費     | 按 instance 開機時數                    | 按實際消耗的 ACU-秒      |
| 擴縮     | 手動改 instance class（有中斷）         | 秒級自動伸縮、無中斷     |
| 離峰成本 | 付滿整台                                | 縮到 min ACU、只付低水位 |
| 適用負載 | 穩定、可預測                            | 間歇、突發、難預測       |

**擴縮行為**：

- 負載上升時 ACU 平滑增加、不需要切換 instance、無連線中斷
- 負載下降時縮回低水位、但受 min ACU 下限約束
- min ACU 決定離峰的最低成本與「保留多少暖容量」；max ACU 決定尖峰的上限與成本天花板

> **Scope warning**：「ACU 對應的記憶體比例」「serverless v2 是否能縮到 0」「最小 ACU 粒度」這些屬 AWS vendor 規格、會隨版本演進（auto-pause 等能力陸續調整）、實作時 cross-verify 官方 doc 當前值。本文不含 production case 揭露的 ACU 配置數字。

對應 knowledge card：[peak forecast](/backend/knowledge-cards/peak-forecast/)、[cost per request](/backend/knowledge-cards/cost-per-request/)。

## min / max ACU 的設定權衡

min 與 max ACU 不是隨便設，兩端各自承擔不同風險。

**min ACU 太低**：離峰省錢，但流量回升時從很低的水位往上爬、爬升期間可能容量不足、且 buffer cache 在低 ACU 時被壓縮、回升後 cache 重新暖機、query latency 短暫升高。對延遲敏感、又有規律日週期的 workload，min ACU 不要壓到極限。

**max ACU 太低**：尖峰被天花板卡住、等同 provisioned 的 instance class 上限問題又回來。max ACU 要按「預期尖峰 + 餘量」設，並把它當成成本天花板來監控——max 設太高雖然不會平時就花錢，但失控 query（如缺索引的全表掃描）可能把 ACU 一路推到 max、帳單尖峰。

**暖容量考量**：min ACU 同時決定「保留多少隨時可用的暖容量」。完全不可預測、且要求第一個請求就低延遲的場景，min ACU 要留足暖機水位，不能為了省錢設到最低。

## 混合 cluster：serverless + provisioned 並存

Serverless v2 不是「整個 cluster 要嘛全 serverless、要嘛全 provisioned」。同一個 Aurora cluster 可以混用：writer 用 provisioned 保穩定、read replica 用 serverless v2 吸收讀取尖峰；或反過來。這讓 workload 的不同部分各取所需：

- 穩定的寫入路徑用 provisioned instance、成本可預測
- 間歇的讀取分析、報表副本用 serverless v2、平時縮到低水位
- failover 目標可指定 provisioned 或 serverless，依可用性需求

混合配置的判讀是把 cluster 內每個角色當獨立的負載形狀評估，而非整個 cluster 一刀切。

## 操作流程

從負載形狀評估到上線的 6 步流程。

#### Step 1：判斷負載形狀

用 CloudWatch 過去 30 天的 CPU / connection / IOPS，看負載是穩定平緩、規律日週期、還是不規則突發：

- 穩定高負載（平均使用率高、波動小）→ provisioned 通常更划算
- 間歇 / 突發 / 開發測試 / 多租戶各自小 DB → serverless v2 適合
- 規律日週期（白天高晚上低）→ serverless v2 或 provisioned + scheduled 都可，算成本 crossover

#### Step 2：估 min / max ACU

min 依離峰最低負載 + 暖容量需求；max 依尖峰負載 + 餘量。第一次設保守一點、上線後依實際 ACU 曲線收斂。

#### Step 3：建立或轉換

```bash
# 新 cluster 指定 serverless v2 capacity range
aws rds create-db-cluster \
  --db-cluster-identifier my-cluster \
  --engine aurora-postgresql \
  --serverless-v2-scaling-configuration MinCapacity=2,MaxCapacity=32
```

既有 provisioned cluster 可加 serverless v2 reader、逐步驗證再調整 writer。

#### Step 4：觀察 ACU 曲線

上線後盯 `ServerlessDatabaseCapacity`（即時 ACU）與 `ACUUtilization`，確認伸縮符合負載、min/max 設定合理。

#### Step 5：成本對照

把實際 ACU-秒換算的帳單，跟「同等 provisioned instance 全時段開機」對照。若 serverless 帳單接近或超過 provisioned，代表負載其實夠穩定、該回 provisioned。

#### Step 6：驗證點

```text
# 驗證離峰真的縮到 min ACU（看 ServerlessDatabaseCapacity 低谷）
# 驗證尖峰沒撞 max ACU 天花板（看是否長時間貼著 max）
# 驗證回升期 latency 可接受（min ACU 暖容量是否足夠）
```

**Rollback boundary**：serverless v2 與 provisioned 可互轉、reader 先轉驗證再動 writer；轉換本身有短暫中斷，要排 maintenance window。

## 失敗模式

production 常見的 5 個踩雷：

#### Case 1：穩定高負載用 serverless 反而更貴

把一個 7x24 高使用率的 cluster 改 serverless「以為省錢」，實際 ACU 幾乎全時段貼近高水位、按 ACU-秒計費比固定 instance 貴。修法：穩定高負載用 provisioned；serverless 的省錢前提是「有顯著的離峰可以縮」。

#### Case 2：min ACU 設太低、回升期 latency 尖刺

離峰縮到極低、早上流量回來時 cache 冷、ACU 從低水位爬、前幾分鐘 query 變慢。修法：規律日週期的 workload，min ACU 留足暖容量；或用 provisioned + scheduled scaling 處理可預測的日週期。

#### Case 3：max ACU 沒當成本天花板監控

缺索引的 query 觸發全表掃描、ACU 一路衝到 max、帳單尖峰才發現。修法：max ACU 設合理上限 + CloudWatch alarm 盯 ACU 長時間貼 max（那是 query 或容量問題的訊號，不是正常擴縮）。

#### Case 4：把 serverless 當「不用做容量規劃」

以為 serverless 自動伸縮就不必估容量、min/max 隨便設。修法：serverless 改變的是「不用手動切 instance」，不是「不用理解負載形狀」；min/max 仍要基於負載曲線設定。

#### Case 5：對延遲極敏感的 OLTP 全 serverless

核心交易路徑要求穩定低延遲、卻用會伸縮的 serverless writer、伸縮邊界期間 latency 抖動。修法：穩定低延遲的核心寫入用 provisioned writer，serverless 留給可容忍伸縮抖動的讀取 / 分析副本（混合 cluster）。

**Anti-recommendation**：負載穩定、使用率長期偏高、或對延遲抖動零容忍的核心 OLTP → 用 provisioned；serverless v2 的價值在「間歇、突發、難預測、或有大量離峰」的負載，沒有離峰可縮就沒有省錢空間。

## 容量與觀測

CloudWatch metric：

- `ServerlessDatabaseCapacity`：即時 ACU、看伸縮曲線
- `ACUUtilization`：ACU 使用率、判斷 min/max 設定是否合理
- `CPUUtilization` / `DatabaseConnections`：底層負載、對照 ACU 是否跟得上

**判讀**：

- ACU 長時間貼近 max → max 設太低或有失控 query，要查
- ACU 長時間貼近 min 且使用率低 → 負載其實很輕，min 可能可再降、或這個 cluster 適合更小配置
- ACU 幾乎不波動且水位高 → 負載穩定，serverless 沒發揮價值，評估改 provisioned

> **Scope warning**：本文未引用 production case 的 ACU 數字；上述 metric 與判讀屬 vendor 規格 + 通用容量工程。

接回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)、[Aurora 容量規劃要點](/backend/01-database/vendors/aurora/)。

## 邊界與整合

### Serverless v2 vs provisioned + scheduled scaling

兩者都能處理「負載隨時間變」，但適用場景不同：

- **scheduled scaling（provisioned）**：負載 *可預測*（已知的日週期、已知大活動）→ 預先排程改容量，成本最可控
- **serverless v2**：負載 *不可預測*（突發、不規則）→ 自動伸縮吸收，不需預測

可預測的尖峰用 scheduled、不可預測的用 serverless，這跟 [DynamoDB capacity mode](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/) 的 predictable-peak vs flash-sale 判讀同源。

### Sibling 與 cross-link

- [storage-architecture](/backend/01-database/vendors/aurora/storage-architecture/) — serverless 只改 compute 層容量、storage 層 quorum 設計不變
- [read-replica-scaling](/backend/01-database/vendors/aurora/read-replica-scaling/) — serverless reader 吸收讀取尖峰、與 fleet 治理結合
- [Aurora I/O-Optimized cost](/backend/01-database/vendors/postgresql/aurora-io-optimized-cost/) — serverless 算的是 compute（ACU）成本、I/O-Optimized 算的是 storage I/O 成本，兩個成本軸獨立、要分開評估
- [rds-proxy-connection-pooling](/backend/01-database/vendors/aurora/rds-proxy-connection-pooling/) — serverless + Lambda 場景的連線管理
- 替代路由：負載穩定且高 → provisioned；KV access pattern → [DynamoDB](/backend/01-database/vendors/dynamodb/)
- 跟 [Netflix 9.C23](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 互引：polyglot 架構下不同 workload 用不同 Aurora 配置（穩定 OLTP provisioned、間歇副本 serverless）
