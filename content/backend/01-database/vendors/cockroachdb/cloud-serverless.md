---
title: "CockroachDB Cloud Serverless 適用判斷：按用量 vs dedicated 的取捨與 RU 計費結構"
date: 2026-06-02
description: "CockroachDB Cloud 的 serverless（按用量 RU 計費、自動 scale-to-zero）跟 dedicated（固定 cluster、自管容量）解不同的容量壓力。本文走 serverless 的 RU 計費結構與冷啟動 / scale 行為、何時 serverless 何時 dedicated 的判讀軸、用量暴衝的成本失控回退、跟 self-managed（Netflix Platform Team / Hard Rock 賽季擴縮）的責任對照"
weight: 80
tags: ["backend", "database", "cockroachdb", "distributed-sql", "serverless", "cockroach-cloud", "deep-article"]
---

> 本文是 [CockroachDB vendor overview](/backend/01-database/vendors/cockroachdb/) 的 implementation-layer deep article。寫作參照 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。本文聚焦 *Cockroach Cloud serverless 與 dedicated 的取捨判讀、RU 計費結構、冷啟動 / scale 行為、何時用 serverless*。Self-managed 規模化的運維責任（Netflix Platform Team 養 380+ cluster）跟賽季型擴縮（Hard Rock 100 ↔ 33 node）作為 *對照軸* 引用、不重展 self-host 運維細節。

---

## 問題情境：要 managed CockroachDB、但 serverless 跟 dedicated 該選哪個

團隊決定不自管 Raft / backup / upgrade，改走 Cockroach Cloud managed，接著面對的是 serverless 跟 dedicated 兩種 managed 形態的取捨。這個取捨不是「哪個比較好」，而是 *容量壓力的形狀對應哪種計費與 scale 模型*。

Cockroach Cloud serverless 是 *把容量決策從「預先 provision 節點」換成「按實際用量計費 + 自動 scale」* 的 managed 形態。它消去了 cluster sizing 這個決策 — 沒有「要開幾個 node」的問題，資源隨 workload 自動伸縮，甚至閒置時 scale 到接近零。代價是計費單位變成抽象的 Request Unit（RU），用量暴衝時成本跟著暴衝，且共享底層資源帶來冷啟動與性能可預測性的取捨。

dedicated 則保留 *固定的 cluster 容量 + 可預測的計費*，由 vendor 代管運維但容量仍是團隊決策。

讀者進來最常卡的三題：

- serverless 的 RU 計費到底計什麼、怎麼估自己的 workload 會花多少？
- serverless 閒置會 scale 到零，那冷啟動會不會讓第一個請求變慢？
- 什麼 workload 適合 serverless、什麼時候該選 dedicated 或乾脆 self-managed？

這三題的共同核心是 *把 workload 的流量形狀（穩定 vs 突發、可預測 vs 不可預測、高峰 vs 長尾）翻譯成計費與 scale 模型*。

問題情境的對照 trigger 來自兩個 self-managed 規模的 case，它們界定了「什麼時候 serverless / dedicated 都不對、要 self-host」的邊界。

[9.C40 Netflix](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/) 是 self-managed 380+ cluster（case 揭露 380+ 為含非 production 的總數、production cluster 160+），case 明確揭露這需要 *專屬 Database Platform Team*（backup、upgrade、incident response、capacity review），並警示「沒這量級團隊就走 Cockroach Cloud managed、不要 self-host」。這條判讀的反向就是本文的入口 — 大多數團隊沒有 Platform Team，managed 才是合理起點，問題只剩 serverless 還是 dedicated。

[9.C41 Hard Rock Digital](/backend/09-performance-capacity/cases/hard-rock-digital-cockroachdb-sports-betting/) 是 self-managed、賽季型擴縮（高峰 ~100 node、淡季 ~33 node，case 觀察段揭露）。這個 100 ↔ 33 的擺盪是 *已知時間點的年度循環*（NFL / NBA 賽季切換），不是不可預測的突發。case 還揭露合規驅動需要 AWS Outposts 把運算放進州內 — 這把它鎖死在 self-managed。Hard Rock 的形狀正好對照出 serverless 的適配範圍：serverless 擅長 *不可預測* 的突發與長尾閒置，而非 *可預測且需要特定部署位置* 的賽季擴縮。

## 核心機制：RU 計費 + 自動 scale + 冷啟動

### Request Unit：把多維資源用量折算成單一計費單位

serverless 的計費核心是 Request Unit（RU）— 一個把 *CPU、IO、network、storage 存取* 等多維資源用量折算成的抽象單位。每個 SQL 請求依其實際消耗的資源換算成若干 RU，帳單按 RU 總量計。這跟 dedicated「按 provision 的節點數 × 時間」計費是兩種不同的成本心智模型。

RU 模型的好處是 *用多少付多少* — 閒置時段不付運算費。風險是 RU 跟「人類直覺的請求數」不是線性對應：一個全表掃描的 query 可能吃掉相當於上千個點查的 RU。estimate workload 成本時，要以 *資源消耗* 為單位思考，不是以「請求數」。

> **Scope warning**：RU 的具體換算係數、serverless 免費額度、scale-to-zero 的觸發閒置時間、冷啟動延遲量級、serverless 的 region / 一致性 / 規模上限，都屬 Cockroach Cloud 的計費與規格、且隨方案版本演進，三個 anchor case（DoorDash / Netflix / Hard Rock 全為 self-managed）都未揭露 serverless 計費數字。本文只給結構性判讀（RU = 多維資源折算、scale-to-zero 帶來冷啟動），具體數值與當前方案邊界需 cross-verify [Cockroach Cloud Pricing 文件](https://www.cockroachlabs.com/docs/cockroachcloud/plan-your-cluster) 與官方計費頁。

### 自動 scale 與 scale-to-zero

serverless 隨 workload 自動伸縮資源，無需團隊 provision。閒置時可 scale 到接近零，這正是「閒置不付運算費」的來源。對 *突發 + 長閒置* 的 workload（開發 / 測試環境、低流量 side project、流量極不均的早期產品），這個模型把成本壓到只反映實際活躍時段。

scale-to-zero 的代價是冷啟動 — 從近零狀態接到請求時，要先把資源拉起來，第一個請求的延遲高於 warm 狀態。對開發環境這通常可接受；對「閒置後第一個用戶請求就要快」的面向用戶 production 路徑，冷啟動是要先評估的取捨。

### serverless vs dedicated 的責任與成本對照

| 維度         | serverless                 | dedicated                  |
| ------------ | -------------------------- | -------------------------- |
| 容量決策     | 自動 scale、無需 sizing    | 團隊決定 cluster 規模      |
| 計費單位     | RU（按實際資源用量）       | 按 provision 的節點 × 時間 |
| 閒置成本     | 接近零（scale-to-zero）    | 仍付 provisioned 容量費    |
| 冷啟動       | 閒置後第一請求有冷啟動延遲 | 無（容量常駐）             |
| 成本可預測性 | 隨用量浮動、突發時可能暴衝 | 固定、可預算               |
| 性能可預測性 | 共享底層、受鄰居影響       | 專屬資源、更可預測         |

每一行都要回到 workload 形狀判讀。

容量決策這一行是兩種模型的根本差異：serverless 把「要開幾個節點」這個決策從團隊手上拿走，對沒有容量規劃經驗或流量極不可預測的場景能降低團隊的容量規劃負擔；但對流量已知、需要性能可預測的 production，dedicated 的「自己定容量」反而是想要的控制權。

成本可預測性這一行是 serverless 的主要風險面。RU 隨用量浮動意味著 *一次失控的查詢模式、一波爬蟲、一個沒加 LIMIT 的全表掃描* 都會把帳單推高，而 dedicated 的成本上限就是 provisioned 容量。流量可預測的 production，dedicated 的可預算性往往比 serverless 的「用多少付多少」更重要。

## 操作流程：選型判讀、配置、用量驗證

### 第一步：用流量形狀做 serverless / dedicated 初判

選型的判讀軸是 workload 的 *流量形狀*，不是規模大小。

- 流量突發 + 長閒置（dev / test、低流量產品、不可預測早期 workload）→ serverless 的 scale-to-zero 與按用量計費直接受益。
- 流量穩定 + 可預測 + 需要性能可預測 → dedicated 的固定容量與可預算成本更合適。
- 流量大 + 有專屬 Platform Team + 需要跨雲 / on-prem / 特定部署位置（如 Hard Rock 的合規 Outposts）→ 兩種 managed 都不對，走 self-managed（見 vendor overview 的容量規劃段）。

判讀訊號：把過去一段時間的 QPS 畫成時間序列，看「活躍時段佔比」與「峰谷比」。活躍佔比低、峰谷比高 → serverless;活躍佔比高、波動平緩 → dedicated。

### 第二步：serverless 建立 cluster 並設成本上限

serverless 的成本風險來自用量浮動，所以建立後第一件事是設 *消費上限*，把「用量暴衝 = 帳單暴衝」的尾部風險封住。

驗證點：cluster 建立後，確認消費上限已設、且設了接近上限的告警閾值（例如達上限 80% 告警）。沒設上限的 serverless cluster 等於把成本曝險完全交給 workload 行為。

### 第三步：驗證 RU 消耗與預期一致

上線後監控 RU 消耗速率，對照第一步的流量形狀預估。

驗證點：RU 消耗速率若遠高於預估，通常是某類 query 的資源消耗被低估（全表掃描、缺索引、N+1 查詢）。這時要回到 query 層優化，而非直接加預算 — serverless 的計費把「低效 query」直接翻譯成「高帳單」，是一個比 dedicated 更直接的成本訊號。

### 第四步：評估冷啟動對 production 路徑的影響

若 serverless cluster 服務面向用戶的 production 路徑，驗證閒置後第一個請求的延遲是否在 SLO 內。

驗證點：模擬閒置後的首請求延遲，對照面向用戶路徑的 latency SLO。超出 SLO 代表這條路徑不適合 scale-to-zero，要嘛保持一定 warm 流量、要嘛改 dedicated。

## 失敗模式：成本失控與選型誤判

### RU 用量暴衝、帳單失控（高代價情境的回退敘事）

serverless 最常見的事故是 *帳單暴衝* — 一波非預期流量、一個低效查詢上線、一次爬蟲，把 RU 消耗推到遠超預算。跟 dedicated「成本上限 = provisioned 容量」不同，serverless 的成本上限要靠人為設定，沒設就沒有天花板。

這個情境的回退代價特殊之處在於 *成本已經發生*：rebalance 可以暫停、locality 可以改回，但已計的 RU 帳單不會退回。所以 serverless 成本失控的「回退」重點在 *事前封頂* 與 *事中熔斷*，而非事後補救。

回退與防護要素：

- 事前一定設消費上限與分級告警（接近上限前就要收到訊號），把尾部風險封在可承受範圍。
- 事中發現 RU 暴衝，先定位來源 — 是流量真的漲（業務事件），還是某個 query 模式失控（缺索引、全表掃描、無 LIMIT）。前者考慮是否該轉 dedicated，後者回 query 層修。
- 設「RU 消耗速率超過閾值就告警 + 自動限流」的 tripwire，避免單一失控 query 在無人值守時段燒完整月預算。
- 若 workload 已穩定成長到「serverless 浮動成本 > dedicated 固定成本」的交叉點，規劃轉 dedicated。

### serverless → dedicated 遷移的代價

當 workload 從「突發長尾」成長為「穩定高量」，serverless 的按用量成本會超過 dedicated 的固定成本，此時要遷移。這個遷移不是改個開關 — serverless 與 dedicated 是不同的 cluster 形態，遷移意味著資料搬遷與 cutover，要走 backup / restore 或資料複製流程，並承擔 cutover 窗口。

回退敘事：把 serverless → dedicated 當成一次小型 migration 規劃 — 估資料量與遷移窗口、雙寫或 backup/restore 路徑、cutover 條件與回退條件，而非「線上無痛切換」。提早在用量逼近成本交叉點時規劃，避免在帳單已經失控時倉促遷移。

Anti-recommendation：不要因為「serverless 聽起來更現代」就把已知穩定、可預測、高流量的 production workload 開在 serverless。這類 workload 的可預算性與性能可預測性，dedicated 給得更直接，serverless 反而引入成本浮動與冷啟動兩個非必要風險。

### 把賽季型 / 可預測擴縮誤當 serverless 場景

可預測的擴縮（如 Hard Rock 的 NFL / NBA 賽季 100 ↔ 33 node 年度循環）不是 serverless 的適配範圍。serverless 擅長 *不可預測* 的突發，而可預測的擴縮可以用 dedicated 的計畫內 scale 直接規劃容量、保留性能可預測性。把可預測擴縮交給 serverless，是用「成本浮動 + 冷啟動」換一個本來就能用排程解決的問題。

修法：可預測的容量循環，用 dedicated + 排程 scale；只有真正不可預測的突發長尾才用 serverless。

### 冷啟動拖垮面向用戶路徑

scale-to-zero 的 serverless cluster 服務面向用戶 production，閒置後首請求冷啟動延遲超出 SLO，用戶感受到第一次訪問特別慢。

修法：面向用戶且對首請求延遲敏感的路徑，要嘛維持低頻 warm 流量避免完全 scale-to-zero，要嘛改 dedicated；scale-to-zero 留給容忍冷啟動的 dev / test / 後台 batch 路徑。

## 容量與觀測

### 必看 metric

- `RU 消耗速率`：serverless 成本的直接訊號，速率異常上升要立刻定位 query 來源。
- `當期累計消費 vs 上限`：成本封頂的剩餘空間，逼近上限要告警。
- `冷啟動 / 首請求延遲`：scale-to-zero 對面向用戶路徑的影響。
- `query 資源消耗分佈`：哪些 query 吃掉最多 RU，是 serverless 成本優化的入口。

### 容量與成本判讀

- serverless 月成本 ≈ Σ(各 query RU × 頻率)，所以成本優化等於 query 效率優化 — 缺索引、全表掃描在 serverless 直接體現為帳單。
- serverless / dedicated 成本交叉點 ≈ 「serverless 浮動成本」與「dedicated 固定容量成本」相等的用量水準，逼近交叉點是規劃遷移的訊號。
- dedicated 的容量規劃回到節點數 × replica × latency budget（見 vendor overview 容量規劃段）。

> **Scope warning**：RU 換算係數、免費額度、serverless 的規模 / region / 一致性上限、serverless ↔ dedicated 成本交叉點的具體用量水準，均為 Cockroach Cloud 計費與規格、隨方案版本變動，非 case 揭露數字，成本建模前以 [Cockroach Cloud 文件](https://www.cockroachlabs.com/docs/cockroachcloud/) cross-verify。

### 回路徑

- [9.6 容量規劃模型](/backend/09-performance-capacity/) 流量形狀 → 計費模型對應。
- [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/) managed vs self-managed 的人力 + 資源成本權衡。

## 邊界與整合

### Sibling deep articles

- [survival goals](../survival-goals/)：managed 形態下 survival goal 仍是團隊決策 — serverless / dedicated 都要對齊業務 RTO / RPO，存活機制以該文為 SSoT。
- [multi-region table config](../multi-region-table-config/)：serverless 與 dedicated 對 multi-region table locality 的支援邊界不同，跨 region 強一致需求要先確認所選 managed 形態是否覆蓋。
- [aurora-dsql-spanner-decision-tree](../aurora-dsql-spanner-decision-tree/)：Aurora DSQL 本身是 serverless distributed SQL，三家 managed distributed SQL 的選型對比以該文為 SSoT，本文不重展。

### 跟 Aurora DSQL / Spanner serverless 對照

Aurora DSQL（AWS）以 serverless 為核心形態、AWS-only；Spanner 提供 managed 但計費與 scale 模型不同。三家在 serverless / managed 維度的完整對比是 [aurora-dsql-spanner-decision-tree](../aurora-dsql-spanner-decision-tree/) 的 SSoT，本文只處理 Cockroach Cloud 自身的 serverless / dedicated 取捨。

### 跟 self-managed 對照

self-managed（如 Netflix 380+ cluster、Hard Rock 合規 Outposts）給最大控制權（跨雲 / on-prem / 特定部署位置），代價是專屬 Platform Team 的運維責任。判讀軸：沒有 Platform Team → managed（serverless / dedicated）；有 Platform Team + 需要特定部署位置或跨雲 → self-managed。

### 1.x 章節互引

- [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 上游選型。
- [PostgreSQL → CockroachDB migration](/backend/01-database/vendors/postgresql/migrate-to-cockroachdb/) — 從 PostgreSQL 遷入後再選 managed 形態。

### 何時不用本文

- 已決定 self-managed（有 Platform Team 或需要 on-prem / 合規 Outposts）→ 看 vendor overview 容量規劃段與 self-host 運維，本文的 serverless / dedicated 取捨不適用。
- single-region 小 workload 且 PostgreSQL 已夠用 → 先確認是否真需要 distributed SQL，見 vendor overview 不適用場景。

## 相關連結

- [CockroachDB vendor overview](/backend/01-database/vendors/cockroachdb/)
- [9.C40 Netflix](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/)（self-managed 需 Platform Team 的反向 = managed 入口）
- [9.C41 Hard Rock Digital](/backend/09-performance-capacity/cases/hard-rock-digital-cockroachdb-sports-betting/)（可預測賽季擴縮 vs serverless 突發適配範圍的對照）
- [distributed SQL 卡](/backend/knowledge-cards/distributed-sql/)
- 官方：[Cockroach Cloud Documentation](https://www.cockroachlabs.com/docs/cockroachcloud/) / [Plan Your Cluster](https://www.cockroachlabs.com/docs/cockroachcloud/plan-your-cluster)
