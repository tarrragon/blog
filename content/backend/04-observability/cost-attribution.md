---
title: "4.15 Cost Attribution / Chargeback"
date: 2026-06-22
description: "把 observability 成本拆到團隊、產品、環境維度"
weight: 15
tags: ["backend", "observability"]
---

## 大綱

- 為何需要 attribution：共享平台模式下成本無人擁有
- 拆分維度：team / service / environment / tenant / cost driver
- 拆分的訊號來源：metric label / log tag / span attribute
- Showback vs chargeback
- Attribution dashboard 設計
- Vendor 帳單拆分能力
- 反模式

## 概念定位

Cost attribution 是把 observability 成本拆回團隊、服務、環境與成本來源的治理能力，責任是讓使用訊號的人也看見訊號成本。

Observability 平台（自架或託管）的成本來自三個層面：ingestion（收了多少資料）、storage / retention（保留了多久）、query（查了多少次跟多大範圍）。沒有 attribution 時，這三層的成本由平台團隊背，產品團隊把 observability 當免費資源 — 新增 metric label、延長 retention、加 dashboard panel 都沒有成本意識。

跟 [4.7 cardinality](/backend/04-observability/cardinality-cost-governance/) 的分工：4.7 是技術治理工具（控制 cardinality、sampling、retention 階梯），4.15 是組織治理工具（讓成本對應到 owner、驅動 owner 採取行動）。

## 拆分維度

### 按 service / team

最基本的拆分。每個服務產生的 ingestion 量（events/sec、series count、log volume）歸到服務 owner。團隊是多個服務的集合。

實作方式：metric 跟 log 的 `service` label / tag 是拆分的基礎。如果 label 穩定且全覆蓋，用 `sum by (service)` 就能拆分 ingestion 成本。Label 不穩定（部分服務沒打 service tag）或 label 值漂移（service name 改名但 cost 系統沒更新）會讓拆分不準。

### 按 environment

Production / staging / dev 環境的成本各自歸因。常見發現是 staging 環境的 observability 成本跟 production 相當 — staging 開了跟 production 一樣的 retention、sampling 率、dashboard，但 staging 的觀測需求遠低於 production。

可操作的做法：staging 跟 dev 環境用更短的 retention（7 天 vs production 的 30 天）、更高的 sampling 比例、關閉不需要的 dashboard。把 environment 的成本差異展示在 attribution dashboard 上，讓團隊自行判斷 staging 的 observability 是否過度。

### 按 cost driver type

Ingestion / storage / query 三層的成本增長模式不同、控制手段也不同。

**Ingestion 成本**：跟 events/sec 跟 series count 成正比。控制手段是 sampling、cardinality 限制、低價值訊號過濾。歸因到產生訊號的服務。

**Storage / retention 成本**：跟資料量 × 保留期成正比。控制手段是 retention 階梯（[4.7](/backend/04-observability/cardinality-cost-governance/)）、[rollup](/backend/knowledge-cards/rollup/) 跟 [storage tiering](/backend/knowledge-cards/storage-tiering/)。歸因到資料保留政策的 owner。

**Query 成本**：跟查詢次數 × 掃描量成正比。控制手段是 [recording rule](/backend/knowledge-cards/recording-rule/)、query cache、query cost estimation（[4.23](/backend/04-observability/observability-query-design/)）。歸因到 dashboard 跟 alert rule 的 owner。

三層分開歸因的價值是精確定位成本增長來源。「這個月成本增長 30%」→ 是 ingestion 增長（某服務開了新 metric）還是 query 增長（某人加了 heavy dashboard panel）？分層歸因讓回答這個問題只需要查一個 dashboard。

### 按 tenant（多租戶場景）

Multi-tenant 平台的 observability 成本跟 tenant 的活躍度有關。大 tenant 產生的事件量可能是小 tenant 的 100 倍，但如果 observability 成本平攤，小 tenant 補貼大 tenant。

Tenant-level attribution 需要 metric / log / trace 帶 tenant label。Label 的 cardinality 問題在 [4.7](/backend/04-observability/cardinality-cost-governance/) 處理 — tenant label 在 metric 層通常過高 cardinality（每個 tenant 一條 series），可以改在 log 或 trace 層按 tenant 統計 ingestion 量。

## Showback vs Chargeback

**Showback**：讓團隊看到自己產生的 observability 成本，但不實際扣款。透明化驅動行為改變 — 當 team A 發現自己的 log ingestion 成本是其他團隊的 5 倍時，自然會開始檢視「是不是 debug log 開太多」。

**Chargeback**：把 observability 成本從團隊的預算中實際扣除。驅動力更強，但需要精確的 attribution（誤差會讓團隊不信任系統）跟組織層面的支持（財務流程、管理層買單）。

多數團隊的起步方式是 showback。Showback 的 attribution 精度要求比 chargeback 低 — 差 10-20% 的歸因不影響行為改變的驅動力。Chargeback 需要差 < 5% 才能讓團隊接受。

## Attribution Dashboard 設計

Attribution dashboard 回答三個問題：

1. **誰在燒？** — 按 service / team 排序的成本排行榜。前 10 個服務通常佔 70-80% 的成本。
2. **燒在哪一層？** — 前 10 個服務的 ingestion / storage / query 成本比例。
3. **趨勢是什麼？** — 月對月的成本趨勢、哪些服務的成本增長最快。

Dashboard 的更新頻率可以低（每天或每週），因為 attribution 驅動的是策略決策而非即時操作。Panel 讀 pre-aggregated 資料（daily cost summary table），查詢成本本身很低。

Attribution dashboard 的 owner 是 observability platform team，但 actionable insight 的 owner 是各服務團隊。Platform team 負責維護 attribution 的精確性跟 dashboard 的正確性；服務團隊負責看自己的成本趨勢跟採取控制行動。

## Vendor 帳單拆分能力

| Vendor                 | 帳單拆分能力                                                 | 限制                          |
| ---------------------- | ------------------------------------------------------------ | ----------------------------- |
| Datadog                | Usage attribution by tag（service / team / env）             | 需要事先定義 attribution tag  |
| Honeycomb              | Team-based usage tracking                                    | 按 dataset 拆分、不按 service |
| Grafana Cloud          | Usage dashboard by data source                               | 需自建 attribution layer      |
| 自架 Prometheus + Loki | 自建 cost model（series count × price / log volume × price） | 完全自定義但維護成本高        |

自架的 attribution 精度最高（因為完全可控），但維護成本也最高。託管 vendor 通常提供 service 或 team 級的 usage attribution，但跨 ingestion / storage / query 的分層拆分需要用 vendor API 自建 dashboard。

## 核心判讀

Cost attribution 的核心目標是讓成本對應到能採取行動的 [owner](/backend/knowledge-cards/ownership/) — 成本只有總額而無歸屬時，沒有團隊有動力控制。

重點訊號包括：

- Ingestion、retention、query 是否能分開歸因
- Team / service / environment label 是否穩定
- Showback 是否足以改變行為，或需要 chargeback
- 高成本訊號是否能對應事故、SLO 或除錯價值

## 判讀訊號

- 成本季度增長、無人能說「哪個團隊 / 服務在燒」
- 高成本服務跟高價值服務不對應、無 ROI 視角
- 平台團隊背所有預算、產品團隊把 observability 當免費資源
- Attribution dashboard 存在但無 owner、半年沒看
- Vendor 帳單只有總額、無服務級拆分
- Staging 的 observability 成本跟 production 相當但無人注意

## 反模式

| 反模式                 | 表面現象                                | 修正方向                                     |
| ---------------------- | --------------------------------------- | -------------------------------------------- |
| 平台吸收所有成本       | 產品團隊沒成本意識、ingestion 無限增長  | Showback 起步、讓團隊看到自己的成本          |
| Attribution 顆粒度太粗 | 只有總額、定位成本來源要人工拆帳        | 按 service + cost driver type 拆分           |
| Chargeback 精度不夠    | 團隊質疑歸因結果、不信任系統            | 先用 showback、精度穩定後再轉 chargeback     |
| Attribution label 漂移 | Service name 改了但 cost 系統沒更新     | Label 同步機制 + 定期 reconciliation         |
| 成本只看帳單不看 ROI   | 砍最貴的 metric 但那是 SLO 唯一訊號來源 | 成本決策同時評估「砍掉後事故定位會變慢多少」 |

## 交接路由

- [4.7 cardinality / cost](/backend/04-observability/cardinality-cost-governance/)：技術層面的成本治理工具
- [4.11 telemetry pipeline](/backend/04-observability/telemetry-pipeline/)：pipeline 各層的成本歸屬
- [4.18 operating model](/backend/04-observability/observability-operating-model/)：platform team 跟 service team 的 cost ownership
- [4.23 觀測查詢設計](/backend/04-observability/observability-query-design/)：query 成本的 estimation 跟治理
- [6.9 capacity / cost](/backend/06-reliability/capacity-cost/)：observability 成本作為整體容量規劃的一部分
