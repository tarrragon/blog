---
title: "9.C41 Hard Rock Digital：CockroachDB on AWS Outposts、Wire Act 合規 + 跨州單一邏輯 DB"
date: 2026-05-26
description: "Hard Rock Digital 用 CockroachDB 跨 AWS Outposts + US-East-1、Wire Act 強制資料留州、單一邏輯 DB 解多州 sportsbook、100 node 32 vCPU 撐 Super Bowl"
weight: 41
tags: ["backend", "performance", "capacity", "case-study", "db-oltp", "aws", "event-peak"]
---

這個案例的核心責任是說明「合規強制資料留地理邊界 + 想要單一邏輯 DB」如何用 distributed SQL + 邊緣硬體解。跟 [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 對比 — Standard Chartered 走「Aurora 多 region、each region 一個 cluster」、Hard Rock Digital 走「跨 AWS Outposts + AWS region 一個邏輯 cluster」。兩條都解受監管金融類業務、結構差異反映法規顆粒不同：銀行是國家層級、美國運動博彩是 *州* 層級。

## 觀察

Hard Rock Digital sportsbook 部署的關鍵數字（引自 [Hard Rock Digital customer page](https://www.cockroachlabs.com/customers/hard-rock-digital/) / [How Hard Rock Digital built a highly available and compliant sports betting app](https://www.cockroachlabs.com/blog/highly-available-sports-betting-app/)）：

| 指標             | 數字                                                              |
| ---------------- | ----------------------------------------------------------------- |
| 營運州數         | 8（AZ / IN / TN / FL / OH / IL / NJ / VA）                        |
| 高峰節點數       | ~100 nodes、each 32 vCPU                                          |
| 淡季節點數       | scales down ~33 nodes（約 1/3）                                   |
| 基礎設施組合     | AWS Regions + AWS Local Zones + AWS Outposts（按州合規要求布局）  |
| 資料庫拓樸       | 跨所有 region 一個 logical database                               |
| Survival goal    | 單一 Outpost 或 AWS AZ 失敗不丟資料                               |
| 顯著測試失敗事件 | node crash / EC2 instance fail / single state loss — 對使用者無感 |
| 重大事件流量     | Super Bowl / World Cup 等高峰、無效能退化紀錄                     |
| Engineering 團隊 | tech team ~50 人；若用 PostgreSQL 估計需多加 10-20 工程師         |

服務組合：CockroachDB self-managed、AWS US-East-1（共用 control plane）、AWS Outposts（部分州合規要求設備位於州內）、AWS Local Zones（特定都會區延遲補強）。

關鍵 workload：bet placement、bet settlement、account management、cache loading、sports metadata import。

關鍵負載形狀：sports betting 是 *event-driven peak* — Super Bowl / World Cup 等賽事是已知時間點、流量在開賽前 30-60 分鐘飆升、賽中持續高水位、賽後 settlement 集中爆發。「100 → 33 → 100」的 scale up / down 反映賽季 vs 淡季的容量需求差。

## 判讀

Hard Rock Digital 的工程選擇揭露三個受監管 OLTP 的設計重點。

1. **法規顆粒決定基礎設施拓樸、不是反過來**：美國 Wire Act 要求 *betting data 必須在下注州內處理*、所以每個營運州都要有州內運算資源。傳統路徑是「每州一個獨立 silo」— 但 silo 之間的玩家統一帳戶、跨州 reporting、欺詐偵測會撞牆。Hard Rock Digital 用 AWS Outposts 把運算放進州內、但邏輯上仍是 *一個* CockroachDB cluster — region placement 配置決定哪些 range 釘在哪個 Outpost、合規與單一邏輯 DB 同時成立。對應 [01.4 database migration playbook](/backend/01-database/database-migration-playbook/) 的合規 boundary 設計與 [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 的 region placement。
2. **Survival goal 「Outpost 或 AZ 失敗不丟」對應業務 SLO**：sports betting 中 *bet placement* 不能 lose — 玩家下注後系統 crash 沒紀錄、對博彩牌照是合規事故。CockroachDB Raft 3-replica + 跨 AZ 配置讓 Outpost 失敗時其他 replica 還在、自動 failover。對應 [06 reliability](/backend/06-reliability/) 的 RPO=0 設計與 [CockroachDB vendor](/backend/01-database/vendors/cockroachdb/) 的 Survival Goals。
3. **Scale up / down 是賽季常態、不是異常事件**：100 → 33 → 100 的擺盪在 sportsbook 業務是 *年度循環* — NFL 季結束 / NBA 季初切換、流量結構性下降。CockroachDB 加減節點靠 range rebalance、不停服。對應 [9.6 容量規劃模型](/backend/09-performance-capacity/) 的 seasonality 與 [9.11 高峰事件準備](/backend/09-performance-capacity/) 的 event-driven scaling。

需要警惕：

- case study 沒揭露 QPS、p99 latency 具體數字。100 node × 32 vCPU 是硬體規模、不是 throughput。讀案例時要區分 *容量 sizing*（節點數）跟 *workload throughput*（每秒處理量）。
- 「省了 10-20 工程師」是 *估計差距*、不是已 hire 後解雇。對應的是「沒選 PostgreSQL 所以沒招那麼多 DBA」、是機會成本不是節省支出。
- Wire Act 是 *美國聯邦法*、各州還有獨立法規（NJ DGE、NV NGC 等）。Hard Rock Digital 模型適合 *跨州* 合規、不是 *跨國* — 跨國牌照差異更大、不能直接套。

## 策略

可重用的工程做法：

1. **合規 boundary 用 region placement 表達、不是 cluster fragmentation**：當法規要求資料留某地理邊界、優先看 distributed SQL 的 region placement / pin-to-region 能力、不要直接開獨立 cluster。獨立 cluster 解了合規但破壞了業務邏輯（跨州統一帳戶、欺詐偵測、reporting）。對應 [CockroachDB vendor](/backend/01-database/vendors/cockroachdb/) 的 multi-region table 與 [Spanner vendor](/backend/01-database/vendors/spanner/) 的 placement。
2. **邊緣硬體（AWS Outposts / Local Zones）是合規工具、不是 latency 工具**：Outposts 主要為「資料留某地理邊界」而存在、latency 改善是副作用。決策時先看合規驅動力、latency 改善列為 bonus。對應 [05 部署平台模組](/backend/05-deployment-platform/) 的 hybrid cloud 設計。
3. **賽季型擴縮容寫進 baseline 容量模型**：Hard Rock Digital 100 ↔ 33 的擺盪不是「臨時 scale up」、是計畫內年度循環。容量規劃要直接把 NFL / NBA / 國際賽事曆塞進預測模型、不要當 surprise。對應 [9.6 容量規劃模型](/backend/09-performance-capacity/) 與 [9.C2 GR8 Tech 體育博彩 AI 預測](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/)。
4. **distributed SQL 的 ops 槓桿：team 小、cluster 大**：Hard Rock Digital 50 人 tech team 養全部運維、估省了 10-20 個 DBA。distributed SQL 把「DBA 養單區、跨區 sync 養運維」的工作量壓進 *系統內建* 的 Raft / placement、人月支出降。對應 [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/) 的人力成本工程化。

跨平台等效：

- Spanner（GCP）也支援 region placement、但 GCP-only、無 Outposts 等效
- Aurora DSQL（AWS 2024）支援跨 region 強一致、但 Outpost 部署現階段未完整覆蓋
- 自管 PostgreSQL + application 層 sharding：理論可行、operation burden 跟人力需求大幅上升、Hard Rock Digital 評估後選 CockroachDB 的主因之一

## 下一步路由

- 對照其他受監管金融 / 博彩 OLTP → [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/)（銀行國家層級）/ [9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/)（fantasy sports）
- 對照 event-driven peak 設計 → [9.C2 GR8 Tech](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/) / [9.C28 FanDuel](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/)
- 想規劃 multi-region OLTP survival goal → [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) + [CockroachDB vendor](/backend/01-database/vendors/cockroachdb/)
- 對照其他 distributed SQL 案例 → [9.C39 DoorDash](/backend/09-performance-capacity/cases/doordash-cockroachdb-orders-platform/) / [9.C40 Netflix](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/) / [9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/)
- 想理解合規驅動的拓樸設計 → [05 部署平台模組](/backend/05-deployment-platform/) + [01.4 database migration playbook](/backend/01-database/database-migration-playbook/)
- 想拆 CockroachDB survival goal 與合規拓樸對齊 → [CockroachDB survival goals](/backend/01-database/vendors/cockroachdb/survival-goals/)
- 想做 region pinning 與在地化 schema → [CockroachDB locality-aware schema](/backend/01-database/vendors/cockroachdb/locality-aware-schema/)
- 想對比 Aurora DSQL / Spanner / CockroachDB 給博彩 OLTP → [Aurora DSQL / Spanner / CockroachDB 決策樹](/backend/01-database/vendors/cockroachdb/aurora-dsql-spanner-decision-tree/)

## 引用源

- [Hard Rock Digital: scaling a performant sports betting platform（cockroachlabs.com customer page）](https://www.cockroachlabs.com/customers/hard-rock-digital/)
- [Hard Rock, anytime, anywhere: scaling a performant sports betting platform（PDF case study）](https://downloads.ctfassets.net/00voh0j35590/7dKNWhsW4RjpUlFgzHB8qw/752a22c833c879bca503bbffb2b584c7/CockroachLabs-Hard-Rock-Digital-Case-Study-v2.pdf)
- [How Hard Rock Digital built a highly available and compliant sports betting app](https://www.cockroachlabs.com/blog/highly-available-sports-betting-app/)
- [Building a sports betting application to handle 'Big Game' traffic](https://www.cockroachlabs.com/blog/real-money-gaming-reference-architecture/)
- [CockroachDB for Gambling solutions page](https://www.cockroachlabs.com/solutions/verticals/gambling/)
