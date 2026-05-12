---
title: "9.11 高峰事件準備"
date: 2026-05-12
description: "活動、季節性流量、推廣事件的 capacity readiness 流程"
weight: 11
tags: ["backend", "performance", "capacity", "peak-event"]
---

## 概念定位

高峰事件準備的責任是把「事件臨頭才動手」變成「事前數週流程化準備」。沒有 readiness 流程時、年度活動靠 oncall 撐、出事率高；有流程之後、活動成「routine event」、工程資源穩定釋放。

本章 *是* [9.10 Production-Side 驗證](/backend/09-performance-capacity/production-validation/) 跟 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) 在「事件型場景」的應用組合、不重新建立方法論。要看具體方法回到那兩章、本章聚焦在 *流程整合*。

讀完後讀者能設計一個 T-90 → T-0 的事件準備時程、回答「Black Friday 該怎麼準備、Super Bowl 該怎麼準備、新片發布該怎麼準備」。

## 事件分類：五種負載形狀

不同事件對應不同準備強度、第一步要分類。

**可預期極端峰值**：年度活動、預售、賽事決賽。提前數月已知時間、業務影響大。例：Prime Day、Black Friday、Super Bowl、IPL 決賽。
**事件型不可預期峰值**：賽事高潮、突發新聞、KOL 推廣。時間或大小不完全可預測。例：賽事進球瞬間、KOL 帶貨、突發新聞引發的流量。
**Flash-sale 瞬間爆量**：售票開賣、報名活動、限量搶購。t=0 瞬間爆量、5-30 分鐘結束。例：演唱會售票、限量商品搶購、報名截止前最後一小時。
**產品爆紅 surge**：新 app 紅、病毒擴散。完全不可預期、流量會隨熱度消退。例：Pokemon GO、ChatGPT 爆紅初期、TikTok challenge。
**結構性 surge**：COVID 類外部衝擊、永久 baseline 上移。不會回到舊水準。例：COVID 期間遠距工作工具、烏俄戰爭期間能源類 app。

對應案例：[9.C1 / 9.C13 / 9.C21 / 9.C27 / 9.C29](/backend/09-performance-capacity/cases/)（predictable）/ [9.C2 / 9.C4 / 9.C7 / 9.C28](/backend/09-performance-capacity/cases/)（event）/ [9.C15 / 9.C16 / 9.C17](/backend/09-performance-capacity/cases/)（flash-sale）/ [9.C8 / 9.C18](/backend/09-performance-capacity/cases/)（surge）。

## T-90 → T-0 準備時程

可預期極端峰值的完整準備時程：

**T-90 天**：流量 forecast + 容量計畫敲定。確認預期峰值倍數、確認 headroom 比例、確認跨 region / AZ 分布。產出 *容量計畫文件*。

**T-30 天**：基礎設施 quota 申請。雲端 instance limit、connection pool、API rate limit、DynamoDB throughput、Lambda concurrency 都要 *提前申請*、不能事件當天才發現 quota 不夠。AWS Infrastructure Event Management（IEM）等服務在這階段啟動。

**T-14 天**：第一輪 production-like 壓測。驗證容量計畫是否真的能撐預期峰值、找出第一輪 bottleneck。

**T-7 天**：完整 game day 演練。注入故障場景（DB failure、AZ outage、第三方 quota 耗盡）、驗證降級、failover、rollback 流程。修正最後問題、更新 runbook。

**T-2 天**：pre-scaling 開始。CDN cache pre-warm、Lambda provisioned concurrency 啟動、autoscaler scheduled 開始、DB capacity 預先 scale up。避免事件當天還在 boot。

**T-0 day**：watch room 待命、runbook 開機可執行。所有相關 oncall 跨團隊聯合 channel、dashboard 集中、escalation path 清楚。

**T+7 天**：retro。對比預測 vs 實際、紀錄 incident 跟 near-miss、列下個事件要改的事。寫進 [06 cases](/backend/06-reliability/cases/) 或本模組 cases。

## Pre-scaling 策略

T-2 階段的 pre-scaling 是「不依賴 autoscaler 反應」的容量保險。

**Pre-scaling 涵蓋層次**：

- **ELB warm-up**：請 AWS 預先 warm up ELB，避免流量上來時 ELB 自身需要時間擴容
- **Lambda provisioned concurrency**：預先 boot 一定數量 instance、避免 cold start
- **DynamoDB / Cosmos DB capacity**：scheduled 提前 scale up
- **EC2 ASG**：min instances 提前拉高
- **CDN cache pre-warm**：重要 URL 提前 invalidate / pre-populate
- **DB connection pool**：應用層提前 warm up connection
- **Cache warmup**：把 hot key 提前 populate 進 cache

**Pre-warm window 通常 30 分鐘到 2 小時**、取決於：

- Instance boot time（VM-based 慢、container 快）
- Cache warmup 時間（cold cache 命中率低、要時間 populate）
- Connection pool 預熱（DB connection establish 有 latency）

**事件結束後也要 *scheduled scale down***：autoscaler 通常 scale up 快、scale down 慢、長期 over-provision 浪費錢。

對應案例：[Tixcraft 30 分鐘擴 130 倍](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) — pre-scaling + Auto Scaling Group + AMI prebuild + ELB warmup 組合；[Prime Day pre-scaling](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) — predictive scaling + scheduled scaling 兩種組合。

詳見 [Predictive Scaling 卡片](/backend/knowledge-cards/predictive-scaling/) 跟 [Scheduled Scaling 卡片](/backend/knowledge-cards/scheduled-scaling/)。

## Watch room 設計

T-0 當天的指揮中心、跨團隊聯合 channel。

**人員配置**：

- 跨團隊聯合 channel：app / infra / network / SRE / business / customer support
- 24/7 輪班（國際事件可能跨 24 小時）
- 明確 incident commander（[08.7 incident command roles](/backend/08-incident-response/incident-command-roles/)）

**Dashboard 集中**：

- 流量 dashboard：總 RPS、按 region 拆分、按 endpoint 拆分
- 延遲 dashboard：p50 / p95 / p99 即時、按 service 拆分
- 錯誤 dashboard：error rate、按 endpoint、按 status code
- 成本 dashboard：當前 hourly cost、預估全天 cost
- 業務 dashboard：訂單數、轉換率、收入

**Runbook 隨手可用**：常見問題 → 對應動作的明確指引。不要事件當下還在 wiki 找資料。

**Escalation path**：什麼狀況找誰、多久升級。寫成決策樹、不要靠人記。對應 [08.7 incident command roles](/backend/08-incident-response/incident-command-roles/)。

對應 [Game Day 卡片](/backend/knowledge-cards/game-day/)。

## Vendor 緊急支援

戰略事件可以申請 vendor 工程師待命、是「人力 backup」。

**AWS Infrastructure Event Management（IEM）**：年度重大事件可以申請、提供 pre-scaling 與專屬監控通道。
**GCP Customer Reliability Engineering（CRE）**：戰略客戶的 24/7 工程支援、能即時為客戶補容量。
**Azure Premier Support + CSAM**：對等服務。

**注意**：這類服務通常綁定 enterprise 等級合約、不是所有客戶都能用。設計事件準備時要假設「沒有 vendor 救援」、vendor 是 bonus 而非 primary plan。

對應案例：[GR8 Tech World Cup IEM](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/) — AWS Infrastructure Event Management 在 2022 FIFA World Cup 期間支援；[Pokemon GO CRE](/backend/09-performance-capacity/cases/niantic-pokemon-go-fifty-x-surge-gcp/) — GCP CRE 即時補容量、撐過 50x surge。

## Game day 演練

T-7 階段的核心活動、把 readiness 從計畫變實戰。

**演練場景**：

- 模擬「事件當天 worst case」
- 注入故障：DB primary failure、AZ outage、第三方 quota 達標、network partition
- 演練降級：哪些功能關閉、用戶看到什麼
- 演練 failover：流量切到備援
- 演練 rollback：發現新版本問題、能不能快速回退

**Game day 學習目標**：

- runbook 不夠詳細 → 補
- 訊號不夠 → 加 metric / alert
- 人員不夠 → 排班補
- 工具不夠 → 工程補

對應 [06 cases Shopify game day](/backend/06-reliability/cases/shopify/) — Shopify game day 是業界範本、值得直接參考。

## Event tier 分級

不同事件規模對應不同準備強度、不能一律照 T-90 流程跑。

**Regular event**（每週 promo、small feature launch）：

- scheduled scaling 即可
- 無 dedicated watch room
- 對應 [06.8 release gate](/backend/06-reliability/release-gate/) 的常規 release

**Major event**（季度行銷、新功能發布）：

- pre-scaling + watch room
- 簡化版 T-14 → T-0 流程
- 跨 team coordination

**Critical event**（年度大促、Super Bowl、IPL）：

- 完整 T-90 流程
- vendor IEM + game day
- 24/7 watch room
- C-level visibility

對應案例：[FanDuel](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) regular game → playoff → Super Bowl 三 tier — NFL 賽季 baseline → playoffs 升 2-3x → championship 升 4-5x → Super Bowl 升 5-10x、每 tier 對應不同準備強度。

## 事後 retro

T+7 retro 是讓 readiness 持續改進的關鍵。

**Retro 必答的問題**：

- 流量 forecast 跟實際差多少？（forecast 改進方向）
- 容量 utilization 峰值多少？（headroom 是否合適）
- 有沒有 incident 跟 near-miss？（runbook 更新方向）
- 下個事件要改的事是什麼？

**Retro 產出**：

- forecast 改進建議（給 [9.6](/backend/09-performance-capacity/capacity-planning/)）
- 新 runbook 或 runbook 更新
- 新 monitoring / alert
- 新工程任務（補容量、補工具）

對應 [08.13 post-incident review](/backend/08-incident-response/post-incident-review/) — retro 不只用在 incident、event readiness 也需要。

## 案例對照

| 案例                                                                                                 | 教學重點                        |
| ---------------------------------------------------------------------------------------------------- | ------------------------------- |
| [9.C1 Prime Day](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/)           | 可預期極端峰值教科書範本        |
| [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)        | flash-sale T-2 pre-scaling      |
| [9.C13 Hotstar IPL](/backend/09-performance-capacity/cases/hotstar-ipl-eighteen-million-concurrent/) | 全球直播 watch room             |
| [9.C2 GR8 Tech](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/)          | AWS IEM + 自家 AI 預測組合      |
| [9.C28 FanDuel](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/)         | event tier 分級（playoff → SB） |
| [9.C8 Pokemon GO](/backend/09-performance-capacity/cases/niantic-pokemon-go-fifty-x-surge-gcp/)      | surge 場景的 vendor 救援（CRE） |

## 下一步路由

- 上游：[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) / [9.10 Production-Side 驗證](/backend/09-performance-capacity/production-validation/)
- 跨模組：[06.20 experiment safety boundary](/backend/06-reliability/experiment-safety-boundary/) / [08 事故處理模組](/backend/08-incident-response/)

## 既建知識卡片

- [Predictive Scaling](/backend/knowledge-cards/predictive-scaling/)
- [Scheduled Scaling](/backend/knowledge-cards/scheduled-scaling/)
- [Game Day](/backend/knowledge-cards/game-day/)
- [Peak Forecast](/backend/knowledge-cards/peak-forecast/)
- [Headroom Budget](/backend/knowledge-cards/headroom-budget/)
