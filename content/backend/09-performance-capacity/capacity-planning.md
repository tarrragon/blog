---
title: "9.6 容量規劃模型"
date: 2026-05-12
description: "peak forecast、headroom budget、growth curve、autoscaling sizing"
weight: 6
tags: ["backend", "performance", "capacity", "planning"]
---

## 概念定位

容量規劃的責任是把「未來 N 個月可能多大」翻成「現在該訂多少 capacity」。這層工作不純靠歷史外推、要結合業務 forecast、事件型成長、頂部風險 buffer。

跟 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/) 的關係：9.4 提供「當前配置能撐多少」、9.6 用這個數字加上 forecast 推「該規劃多少」。沒有 9.4 的 baseline、9.6 只是猜；沒有 9.6 的 forecast、9.4 的 baseline 只是 snapshot。

本章是「規劃決策」的章節、不是執行手冊。讀完後讀者能回答：peak 怎麼預測、headroom 訂多少、autoscaler 怎麼配、不可水平擴的服務怎麼處理。

## 容量公式三項

容量規劃的核心公式可以濃縮成三項相乘：`容量 = 預期峰值 × (1 + headroom) / 可擴容速度`。每一項都需要獨立分析：

**預期峰值（peak forecast）**：歷史 baseline × 預期成長 × 事件因子。三項中最影響整體準度。詳見 [Peak Forecast 卡片](/backend/knowledge-cards/peak-forecast/)。

**Headroom budget**：通常 30-50%、為了應付異常 burst + AZ 故障 + forecast 誤差。不同工作負載 headroom 不同。詳見 [Headroom Budget 卡片](/backend/knowledge-cards/headroom-budget/)。

**可擴容速度（reactive vs predictive）**：autoscaler 反應時間 vs 流量上升速度。如果流量上升比 autoscaler 快、必須 *提前* pre-scale、不能等 reactive 反應。

這個公式的另一個寫法是「容量 = peak × 安全係數」、安全係數 = (1 + headroom) / 可擴容速度。預測準 + 擴容快 → 安全係數小、容量緊湊；預測差 + 擴容慢 → 安全係數大、成本高。

## Peak forecast 方法

Forecast 方法分三層、按業務型態選用。

**歷史線性外推**：拿過去 N 個月的趨勢、按斜率外推到下 N 個月。適合 sustained growth（B2B SaaS 月增 X%）；不適合 event peak（年度活動）跟 surge（產品爆紅）。

**季節性分解（STL：Seasonal-Trend decomposition using Loess）**：把長期趨勢、週期成分、殘差分開預測。適合電商（雙 11 / Black Friday）、串流（IPL / Super Bowl）、零售（聖誕節）。需要 *至少兩個完整 cycle* 的歷史資料。

**業務 ML 模型**：結合 marketing pipeline（廣告投入）、新用戶獲取（acquisition rate）、留存率、產品變化等多 feature。最精準但成本高、需要 ML team。

**最常見錯誤是「拿去年同期 × (1 + 預期成長 %)」**：忽略產品改動 + 行銷投入變化 + 外部事件。Prime Day 2025 vs 2024 不只是 +30% — 是 AI shopping assistant 上線、是 ad spend 變化、是新國家上線。

對應案例：[Prime Day 年增率 +30% ~ +77%](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) — 連 Amazon 自家每年成長都不能線性外推；[Disney+ 新片發布](/backend/09-performance-capacity/cases/disney-plus-content-metadata/) — 事件型 forecast、按過去新片 metric 預估。

Forecast 必須有 *誤差範圍*、不能單一數字。給上下界（最壞 / 預期 / 最好）、容量規劃才能用 worst-case 訂 baseline。

## Headroom budget 設計

Headroom 不是 over-provisioning 浪費、是容量規劃的安全邊界。常見比例 30-50%、按 saturation 行為跟工作負載敏感度調整。

**為什麼是 30-50% 而不是 10%**：

- forecast 誤差：預測準度通常 ±20-30%
- burst pattern：瞬間 spike 超過 average peak、需要短時間吸收
- AZ / region failover：一個 AZ 掛、剩下兩個要承擔全部（多 33% 容量）
- 系統老化 / drift：軟硬體升級後 saturation 點可能位移

**不同工作負載不同 headroom**：

- stateless service：30%（autoscaler 反應快、headroom 可以薄）
- DB：50%（不易擴容、要備援足夠空間）
- broker / queue：60%（consumer 落後恢復時要瞬間吃下積壓）
- consensus DB：80%+（完全不能 reactive 擴）

**headroom 太低 → 出事**：peak 期間進 cliff、用戶體驗變差。
**headroom 太高 → 浪費錢**：平日成本拉高、CFO 質疑。

對應案例：[GR8 Tech AI 預測](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/) — 預測準了可以降 headroom 比例；預測不準必須拉高 headroom 補回安全邊界。

## Growth curve 形狀分類

不同 growth curve 形狀對應不同 forecast 方法跟 review 節奏。

**Linear growth**：用戶月增 X%。B2B SaaS 最常見。forecast 線性外推、每季 review、headroom 可以薄（成長可預測）。

**Step growth**：每次行銷 / 活動跳一階、之間 plateau。需要 event tier 規劃、每個事件單獨 forecast、headroom 跟 event 強度連動。

**Exponential growth**：早期初創、病毒擴散。forecast 容易低估、傳統線性外推會大幅低估；headroom 必須拉到 100%+、不能省。

**S-curve growth**：成熟產品、會 saturate。Forecast 初期像 exponential、中期 plateau、晚期 mature。需要識別 inflection point、過了就調 forecast 方法。

**Cyclical**：電商季節性。每年 Black Friday / Cyber Monday / Christmas / Chinese New Year 都重複、forecast 用 STL 季節性分解。

對應案例：[Zoom 30x COVID](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/) — step growth、外部衝擊讓 baseline 永久上移；[Pokemon GO 50x surge](/backend/09-performance-capacity/cases/niantic-pokemon-go-fifty-x-surge-gcp/) — exponential（早期）+ 之後 S-curve；[ASOS Black Friday](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) — cyclical。

詳見 [Growth Curve 卡片](/backend/knowledge-cards/growth-curve/)。

## Autoscaling sizing

訂好 capacity 之後、要設計 autoscaler 把這個容量 *動態使用*。

**min / max / target metric 三個參數**：

- min 太低 → cold start 風險（流量上來時還在 boot）
- min 太高 → 平日浪費
- max 太低 → 限流（peak 時 autoscaler 不能再擴）
- max 太高 → 月底炸帳單（autoscaler 不受控、過 peak 不會主動降）
- target 太高 → autoscale 啟動太晚、進 knee 才反應
- target 太低 → autoscale 太敏感、頻繁 scale up / down 浪費

**Predictive vs reactive**：

- [predictive scaling](/backend/knowledge-cards/predictive-scaling/)：根據歷史 pattern 或 ML 模型提前擴
- reactive scaling：根據當下指標擴
- 兩者組合最穩：predictive 處理已知 pattern、reactive 處理 unexpected burst

**Scheduled vs metric-based**：

- [scheduled scaling](/backend/knowledge-cards/scheduled-scaling/)：時段觸發（年度活動、daily peak）
- metric-based：根據 utilization / queue depth 觸發
- 三層組合（scheduled + predictive + reactive）最穩

**不同層的 autoscaler 各自設計**：

- EC2 Auto Scaling Group：infrastructure 層
- Kubernetes HPA / VPA：pod 層
- Karpenter：node 層
- DynamoDB auto-scaling：DB capacity 層
- CloudFront：CDN 層

對應案例：[Tixcraft 30 分鐘擴 130 倍](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) — 6 台 → 800 台靠 ASG + AMI prebuild + ELB warmup；[Prime Day predictive](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) — pre-scaling 30-77% 年增率提前算進容量。

## 不可水平擴容服務的容量規劃

部分服務不能用「加機器」解決容量問題。這類服務的容量規劃有獨立邏輯。

**典型不可水平擴**：

- consensus DB（RAFT / Paxos）：節點數量是 consensus 一部分、不能臨時增減
- single leader DB（PostgreSQL primary、MySQL master）：寫只有一個 leader
- 中央 coordinator：必須拆解才可擴

**容量公式變成**：單機極限 × headroom、沒有 elastic 救援。
**設計重點**：

- 預先 provision 到能撐 peak、不依賴 reactive 擴
- 垂直擴容（更大 instance）為主、不是橫向
- 留更高 headroom（80%+）、出事沒有第二招

對應案例：[Coinbase pre-provision](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) — RAFT 限制下完全 pre-provision、不 autoscale；[Spanner 節點即容量單位](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) — 雖然全球可擴、但每個 region 內節點數要預先規劃。

## 跨地理 / 跨 region 容量規劃

跨 region 服務不能用 *全球總量* 平攤、每個 region 獨立規劃。

**為什麼不能聚合**：

- 用戶在哪、流量就在哪、不會自動 spread
- 跨 region 切流量有延遲（DNS TTL、用戶習慣）、不能即時 rebalance
- 資料駐留合規可能強制各 region 獨立

**規劃方法**：

- 每個 region 抽各自的 workload model
- 各自跑 saturation discovery
- 各自訂 headroom（區域峰值 + 區域 AZ failover）
- 跨 region failover plan：哪個 region 掛了、流量去哪、目標 region 要留多少 headroom 接

對應案例：[Standard Chartered 7 個受監管市場](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) — 跨市場獨立容量規劃；[Genesys 15 region](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/) — 15 主 region + 5 衛星 region 各自規劃；[Mercado Libre 18 國](/backend/09-performance-capacity/cases/mercado-libre-latam-bigquery-vertex/) — 每國獨立 cycle。

## 案例對照

| 案例                                                                                                  | 教學重點                            |
| ----------------------------------------------------------------------------------------------------- | ----------------------------------- |
| [9.C1 Prime Day](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/)            | 可預期峰值的 forecast + pre-scaling |
| [9.C2 GR8 Tech](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/)           | AI 預測式擴容、縮短反應時間         |
| [9.C18 Zoom](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/)                       | 30x surge 後 baseline 永久上移      |
| [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) | 跨市場獨立容量規劃                  |
| [9.C3 Coinbase](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/)     | 不可水平擴的 pre-provision          |

## 下一步路由

- 上游：[9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/) / [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)
- 下游：[9.7 成本邊界與 efficiency](/backend/09-performance-capacity/cost-engineering/)（容量翻成成本）
- 下游：[9.11 高峰事件準備](/backend/09-performance-capacity/peak-event-readiness/)
- 跨模組：[05 部署平台模組](/backend/05-deployment-platform/) autoscaler 實作

## 既建知識卡片

- [Peak Forecast](/backend/knowledge-cards/peak-forecast/)
- [Headroom Budget](/backend/knowledge-cards/headroom-budget/)
- [Growth Curve](/backend/knowledge-cards/growth-curve/)
- [Predictive Scaling](/backend/knowledge-cards/predictive-scaling/)
- [Scheduled Scaling](/backend/knowledge-cards/scheduled-scaling/)
