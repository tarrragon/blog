---
title: "9.C28 FanDuel：體育直播 + 投注的雙重峰值"
date: 2026-05-12
description: "FanDuel 3.5M MAU、Super Bowl 期間擴容 5-10 倍、用 AWS Local Zones + Wavelength + Outposts 處理 20+ 州的雙重峰值"
weight: 28
tags: ["backend", "performance", "capacity", "case-study", "compute", "aws", "event-peak"]
---

這個案例的核心責任是說明「雙重峰值對齊」的工程取捨。FanDuel 同時運營體育直播（live streaming）跟體育投注（betting）、兩個工作負載在 *同一場 NFL Super Bowl* 同時達到峰值、但 SLO 完全不同 — 直播容忍 30 秒延遲、投注必須毫秒內成交。

## 觀察

FanDuel 在 AWS 的關鍵敘述（引自 [FanDuel Case Study](https://aws.amazon.com/solutions/case-studies/fanduel-case-study/)）：

| 指標         | 數字                                    |
| ------------ | --------------------------------------- |
| 月活客戶     | 3.5 M+                                  |
| 服務地理     | 美國 20+ 州 + 加拿大                    |
| 峰值擴容倍數 | 5-10x（NFL Super Bowl 等大型賽事）      |
| 服務組合     | AWS Local Zones + Wavelength + Outposts |
| 峰值類型     | 直播 + 投注雙峰                         |

關鍵敘述：「seamlessly scale capacity 5–10 times as required for large sporting events, such as the NFL Super Bowl」。

## 判讀

FanDuel 案例揭露三個雙重峰值對齊的工程重點。

1. **直播跟投注是兩種完全不同 SLO**：直播容忍秒級延遲（用 CDN + ABR 串流）、投注必須毫秒級成交（Super Bowl 進球瞬間、賠率變動、用戶投注必須在賠率變化前完成）。兩個服務必須各自獨立擴容、各自獨立 SLO。對應 [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/) 的多 SLO 對齊。
2. **AWS Local Zones / Wavelength / Outposts 是地理 + 監管雙重需求**：美國博彩受各州監管、資料必須留在州內 → 用 Local Zones 在每個州就近部署；4G/5G 用戶投注延遲敏感 → 用 Wavelength 在電信商機房內運算；on-prem 需求 → 用 Outposts。對應 [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 的受監管雙重需求、跟 [9.C12 Riot Games](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/) 的延遲反推 region。
3. **5-10x 是「同類事件中的最高倍率」**：Super Bowl 是 NFL 賽季最大事件、不是常態。平日 baseline → 季後賽 2-3x → 季冠軍賽 4-5x → Super Bowl 5-10x。容量規劃要按事件級別分段、不是一律 10x。對應 [9.6 容量規劃模型](/backend/09-performance-capacity/) 的事件型容量分級。

需要警惕：

- AWS 案例 *沒有* 提具體 betting transaction TPS、concurrent streams、延遲分布。讀者要對 *策略* 學習、不要套用具體數字。
- 「5-10x」是 *峰值倍數*、不是 *peak 持續時間*。Super Bowl 的關鍵 30 分鐘可能 8-10x、其他 3 小時可能 3-5x。

## 策略

可重用的工程做法：

1. **不同 SLO 的工作負載分開部署、不要混在同一 service**：betting 跟 streaming 在 FanDuel 必然是兩個獨立微服務、各自有 dedicated infrastructure。對應 [05 部署平台模組](/backend/05-deployment-platform/) 的 service decomposition、跟 [9.C7 Lyft](/backend/09-performance-capacity/cases/lyft-microservice-eight-x-peak/) 同思維。
2. **多層 edge（Local Zone / Wavelength / Outposts）服務不同延遲需求**：Local Zone 服務「州內合規」需求、Wavelength 服務「電信網內超低延遲」、Outposts 服務「on-prem 監管」需求。三者組合對應跨州博彩業務。
3. **事件型容量規劃分級**：建立 event tier 體系（regular game / playoff / championship / super bowl），每 tier 對應不同 pre-scale 倍數。對應 [9.11 高峰事件準備](/backend/09-performance-capacity/) 的容量分級。

跨平台等效：Azure 提供類似 stack（Stack Edge + Edge Zones + Azure for Operators）、GCP 有 Network Edge + Distributed Cloud。差異是各家 edge 覆蓋深度跟電信商合作。

## 下一步路由

- 對照其他事件型峰值 → [9.C2 GR8 Tech](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/)（賽事高潮 AI 預測）/ [9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/)
- 想設計多 SLO 對齊 → [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/)
- 想做受監管多地區部署 → [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) + [9.C12 Riot Games](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/)
- 想做 edge / Local Zone 規劃 → [05 部署平台模組](/backend/05-deployment-platform/)
- 想理解雙峰下 Aurora storage / replica scaling → [Aurora 儲存層架構](/backend/01-database/vendors/aurora/storage-architecture/) + [Aurora read replica scaling](/backend/01-database/vendors/aurora/read-replica-scaling/)
- 想評估 distributed SQL 在 betting 場景的 fit → [Aurora DSQL / Spanner / CockroachDB 決策樹](/backend/01-database/vendors/cockroachdb/aurora-dsql-spanner-decision-tree/)

## 引用源

- [FanDuel Case Study](https://aws.amazon.com/solutions/case-studies/fanduel-case-study/)
- [FanDuel CloudFront Case Study](https://aws.amazon.com/solutions/case-studies/fanduel-cloudfront-case-study/)
