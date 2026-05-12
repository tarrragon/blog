---
title: "9.7 成本邊界與 efficiency"
date: 2026-05-12
description: "cost per request、cost curve、降級成本、over-provisioning trade-off"
weight: 7
tags: ["backend", "performance", "capacity", "cost"]
---

## 概念定位

成本工程的責任是讓容量決策有經濟邊界。沒有成本意識時、容量規劃會「保險起見全部擴」、最終帳單炸裂；有成本意識之後、能 *在每一個容量決策點* 把「多保險」跟「多省錢」一起評估。

跟 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) 的關係：9.6 算「該訂多少容量」、9.7 算「這樣訂值不值得」。兩者必須一起做、不能先決定容量再算成本。

本章從 cost per request 這個 unit economics 開始、推到 cost curve、TCO、降級成本、人力成本工程化、FinOps 整合。讀完後讀者能回答「容量設計的成本邊界在哪、什麼時候該降級而非擴容」。

## Cost per request 模型

雲端帳單從月度視角看是黑箱、從 cost per request 視角看可拆解。

**基本公式**：月帳單總額 / 月總 RPS = cost per request。但這只是平均、不同 endpoint 成本差很大。
**分 stage 拆解**：app compute + DB read + DB write + cache + network egress + 第三方 API。每個 stage 自己有 unit cost。
**分 endpoint 拆解**：登入請求可能 $0.0001、結帳請求可能 $0.001（10x 差距）。原因：結帳走更多 stage、可能跨 region、可能呼叫第三方支付。

**對齊業務 metric**：

- cost per active user：總成本 / MAU
- cost per transaction：總成本 / 完成的訂單數
- cost per ML inference：總成本 / inference 次數

業務 metric 級別的 cost 才能跟收入對比、才能算 unit economics。

對應案例：[Zomato 50% 成本下降](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) — 算出每筆計費事件的 cost per request 後、發現 TiDB over-provision 拖累、遷移 DynamoDB 後減半；[Netflix Aurora 28% 成本降](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) — DB consolidation 把多套 DB 的 cost 統一到 Aurora、Aurora 自己的 cost per request 更便宜。

詳見 [Cost Per Request 卡片](/backend/knowledge-cards/cost-per-request/)。

## Cost curve 形狀

不同 pricing 模式的 cost curve 形狀不同、組合起來才能最佳化。

**On-demand（pay-per-use）**：流量上升、成本同步上升。線性 cost curve。優點：彈性、不用承諾；缺點：單位成本最貴。
**Reserved instances（RI）/ Savings Plans**：承諾 1-3 年用量、單位成本降 30-60%。階梯 cost curve。優點：便宜；缺點：承諾期內如果用量低、浪費。
**Spot instances**：用 cloud 閒置 capacity、單位成本降 70-90%。可被中斷。優點：最便宜；缺點：可能突然被收回。

**最佳組合通常是「Reserved baseline + On-demand spike + Spot batch」**：

- Reserved 覆蓋 baseline 容量（永遠用得到）
- On-demand 處理 peak 跟 unpredicted burst
- Spot 跑 batch 工作（不在 critical path、可被中斷）

對應案例：[Riot Games 年省 1000 萬](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/) — 從自管 Mesos 遷到 EKS、降的不只是 instance cost、是 cluster 管理人力 + ops 簡化；[Capcom 30% 成本下降](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/) — DynamoDB + EKS 取代自管、釋放 DBA 人力。

## Over-provisioning vs under-provisioning 取捨

容量決策的核心經濟學問題：訂多大容量才是最划算？

**Over-provisioning 成本**：每月多付 $X 雲端費。這個數字直接看帳單。
**Under-provisioning 成本**：sigma 機率 × downtime × revenue per minute。這個數字更難算 — 需要 historical incident rate + downtime impact analysis。

**兩個成本平衡點 = 經濟最佳 headroom**。但實務上 under-provisioning 成本不容易量化、保守做法是把 sigma 機率拉高（用 worst-case 估）、headroom 訂寬一點。

**Critical workload**（金融、醫療、付款）：under-provisioning 成本極高（合約違約 + 客戶流失 + 法規）、寧可 over-provisioning 30-50%。
**Non-critical workload**（內部工具、分析、batch）：under-provisioning 成本低、可以更貼近 minimum capacity。

對應案例：[Zomato TiDB 必須 over-provision](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) — 為了應付 spike、TiDB 必須長期 over-provision；DynamoDB on-demand 不必、pay-per-use 自然處理。

## 降級的成本邊界

「降級 vs 擴容」是常見容量決策、但常被當成「技術問題」而非「成本問題」。

**降級不是免費**：

- 流失轉換：UI 顯示「系統忙碌」、用戶可能放棄
- 客訴成本：客服處理客訴的 OpEx
- 品牌損失：社群媒體負面評論、口碑下降
- 合約違約：B2B 客戶可能基於 SLA 求償

**算「降級 vs 擴容」哪個成本低**：

- 擴容成本：peak 時段多付的 cloud 費用
- 降級成本：上述四項合計
- 哪邊低就選哪邊

**降級觸發條件**通常按負載門檻 / 成本門檻 / SLA 觸發：

- 負載門檻：utilization > 85% → 啟動降級
- 成本門檻：本月雲端費已超預算 X% → 啟動降級
- SLA 觸發：error budget 快用完 → 啟動降級保 SLA

對應案例：[Pokemon GO 50x surge](/backend/09-performance-capacity/cases/niantic-pokemon-go-fifty-x-surge-gcp/) — surge 期間無法等比擴容、必須降級保住核心遊戲機制、犧牲附加功能。

## 人力成本工程化

雲端帳單是顯性成本、但 *人力成本* 是常被忽略的隱性容量成本。

**自建 vs managed 的人力成本對比**：

- 自建 Kafka / PostgreSQL / Redis：需要 DBA / SRE 持續維護 + 升級 + 故障處理
- Managed 服務（MSK、Aurora、ElastiCache）：vendor 負責 patch、backup、failover
- 差距通常 *3-10 倍* 人力成本

**DBA / SRE / network engineer 都是隱性容量成本**：

- 一個資深 DBA 在美國年薪 $200K+、台灣 NTD 200-400 萬
- 工程師時間是有上限的、自管系統佔的時間就是 *無法投入產品開發* 的機會成本

**「90% 工程工時下降」是管理 ROI 的關鍵**：不是吹噓技術 — 是把工程資源從 *維持* 轉移到 *建構*。

對應案例：[Spotify Kafka → Pub/Sub](/backend/09-performance-capacity/cases/spotify-kafka-to-pubsub-migration-gcp/) — 不是因為 Pub/Sub 便宜、是因為 Spotify 規模下自管 Kafka 的人力成本不划算；[Lemino 90% 工程工時降](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) — managed 路線讓電信商級新串流服務只用 5-10 個工程師 launch；[Capcom DBA 釋放](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/) — 把 DBA 時間從 patching 轉到遊戲品質。

## FinOps 跟容量規劃的整合

FinOps 是 *財務跟工程的協作框架*、把成本決策從事後對帳變成事前規劃。

**Showback / chargeback**：把雲端成本攤到團隊 / 服務 / feature。每個團隊看得到自己的成本、自然開始 optimize。chargeback（實際扣預算）比 showback（純展示）更有效但組織複雜度高。

**每月 cost review 變成容量 review 的一部分**：

- 對比預算 vs 實際
- 找出 top 5 cost driver
- 對比上月趨勢、看是否有 anomaly
- 跟 capacity team 一起討論 right-sizing

**Spot diversification**：spot 中斷風險可以靠 *多 instance type 跟多 AZ* 分散。例如：spot pool 同時包含 m5.large + m5a.large + m5n.large、各 AZ 都有、單一 type pool 撤回時其他 type 還在。

**Right-sizing**：定期 review instance type 是否最適。常見浪費：訂太大 instance（CPU / RAM 用 30%）、過時 instance generation（用 c5 沒升到 c7）、reserved 過剩。

## 反模式

容量成本的常見錯誤模式：

**Autoscaling max 設無限大**：流量爆衝時 autoscaler 跟著爆衝、月底帳單炸裂。max 必須訂、是 financial circuit breaker。

**全部用 on-demand、沒談 reserved / savings plan**：cloud spending > $10K/月 已經值得跟雲商 talk discount、savings plan 通常 30-60% off。

**沒成本 monitoring、直到帳單來才知道**：要建 daily cost dashboard、anomaly 即時 alert、不要等月帳單。

**降級用人工觸發、出事時來不及**：降級邏輯要 *自動化*、按 metric 觸發、不是 oncall 工程師看到 dashboard 才下指令。

**忘了人力成本**：算 build vs buy 只算 cloud 費、忘了 SRE / DBA 時間、結果發現「省的 cloud 費 < 多花的人力」。

## 案例對照

| 案例                                                                                         | 教學重點                               |
| -------------------------------------------------------------------------------------------- | -------------------------------------- |
| [9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/)    | 50% 成本下降（從 over-provision 解放） |
| [9.C12 Riot Games](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/)     | 年省 1000 萬（EKS 替代 Mesos）         |
| [9.C23 Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)        | 28% 成本下降（DB consolidation）       |
| [9.C29 Lemino](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) | 90% 工程工時降（managed 路線）         |
| [9.C19 Capcom](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/)           | 30% 成本下降（DBA 釋放到遊戲品質）     |

## 下一步路由

- 上游：[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)
- 下游：[9.8 效能可觀測性](/backend/09-performance-capacity/performance-observability/)（cost attribution）
- 跨模組：[04.14 cost attribution](/backend/04-observability/cost-attribution/)

## 既建知識卡片

- [Cost Per Request](/backend/knowledge-cards/cost-per-request/)
- [Headroom Budget](/backend/knowledge-cards/headroom-budget/)
