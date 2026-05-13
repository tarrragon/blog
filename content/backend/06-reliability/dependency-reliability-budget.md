---
title: "6.14 Dependency Reliability Budget"
date: 2026-05-01
description: "把內外依賴的可靠性納入 SLO 計算與設計約束"
weight: 14
tags: ["backend", "reliability"]
---

## 大綱

- 為何依賴需要 budget：自家服務的 SLO 是依賴 SLO 的乘積
- 依賴類別：內部服務、第三方 API、SaaS、基礎設施（DB / cache / queue）
- 依賴 SLA 對照：vendor 公布的 SLA 跟 observed reliability 的差距
- budget 計算：依賴 99.9% × 自家 99.9% = 99.8% 上限
- 降級設計：依賴失效時的 fallback / cache / 隊列緩衝
- circuit breaker 與 budget 的關聯
- 跟 [6.6 SLO](/backend/06-reliability/slo-error-budget/) 的整合：依賴 budget 是 SLO 算式的一部分
- 跟 [4.13 topology](/backend/04-observability/service-topology/) 的整合：依賴拓撲提供 budget 評估資料
- 反模式：SLO 訂目標時忽略依賴可靠性；vendor SLA 抄進合約但無監測；依賴掛了才發現有依賴

## 概念定位

Dependency reliability budget 是把外部服務與跨團隊依賴的可靠性納入設計約束，責任是避免把自己系統的目標建立在不可控前提上。

這一頁處理的是依賴一旦變差，自己服務還能保住多少功能。當依賴不是自己能修的時候，budget 就是把不確定性明文化。

## 核心判讀

判讀依賴風險時，不只看 SLA，而是看依賴失效後的降級能力與 [blast radius](/backend/knowledge-cards/blast-radius/)。

重點訊號包括：

- 依賴是否有明確 failure domain
- 是否有 graceful degradation 或 fallback
- budget 是否會隨依賴變更而更新
- 外部 outage 是否能快速路由到替代策略

## 案例對照

- [AWS S3](/backend/08-incident-response/cases/aws-s3/_index.md)：基礎儲存依賴的邊界一旦縮小，整體可靠性就會被放大影響。
- [Cloudflare](/backend/08-incident-response/cases/cloudflare/_index.md)：edge / control-plane 依賴需要有明確降級路徑。
- [Azure AD](/backend/08-incident-response/cases/azure-ad/_index.md)：身份依賴失效時，影響通常跨產品、跨流程。

## 失效局部化：cell 邊界跟 shuffle sharding

失效局部化是把單一依賴退化限制在最小可影響範圍的能力。把「依賴 budget」從統一全域帳本拆成 per-cell 可用度結構、是這層治理的核心責任。失效局部化要解四個子問題：擴散邊界、熱點重疊、控制面解耦、失敗模式工作量恆定。

對應 [A1 Amazon Shuffle Sharding 與 Cell 邊界](/backend/06-reliability/cases/amazon/shuffle-sharding-and-cell-boundary/)：揭露四個機制對應上述四個子問題 — cell 邊界（擴散邊界）、shuffle sharding（熱點重疊）、static stability（控制面解耦）、constant work（失敗模式工作量恆定）。這四個機制把恢復策略從「全域搶救」轉為「分批收斂」。Cell 邊界是 6.14 SSoT；實驗時 blast radius 的邊界控制由 [6.20 experiment-safety-boundary](/backend/06-reliability/experiment-safety-boundary/) 處理、兩者邊界互補（前者是常態架構、後者是實驗範圍控制）。

把 cell 邊界跟 shuffle sharding 視為依賴 budget 的前置結構：先限制擴散邊界、再談恢復策略。budget 算式裡的「依賴失效」應該對應到「最大可影響 cell」、不是「整個服務全停」。

## 跨區故障跟回復順序

跨區故障的核心責任是把「單區極限失效」跟「跨區連鎖退化」拆成兩個治理面。fault domain 限制單區擴散、ordered failover 控制回復節奏、dependency isolation 切斷共享路徑放大風險、三者構成跨區治理 contract。大規模平台的關鍵風險來自跨區相依引發的連鎖退化 — 單點失效只是觸發點、真正的擴散面在共享相依路徑。

對應 [M1 Meta Region Failover 邊界治理](/backend/06-reliability/cases/meta/region-failover-and-reliability-boundaries/)：揭露三個機制 — region fault domain（影響面最多到哪裡）、ordered failover（先恢復哪條路徑）、dependency isolation（共享相依如何降風險）。

回復順序的核心是分批恢復、不同時恢復所有路徑。同時恢復多條路徑可能在剛恢復的依賴上引發回源放大或連鎖過載、把原本可控的回復變成第二次故障。實際的做法跟 ordered failover 對齊：依事故 timeline 跟團隊既定 runbook 安排回復批次、每批驗證 baseline 穩定後再進下一批。具體的批次設計跟 ordered failover 證據交給 [8.3 containment-recovery-strategy](/backend/08-incident-response/containment-recovery-strategy/)。

## 跨團隊 reliability 契約

跨團隊 reliability 契約的核心責任是讓「依賴 budget」變成「契約欄位」：每個被依賴的服務承諾哪些 SLI、提供哪些降級路徑、failure mode 是什麼。團隊自治程度高的組織需要共同契約把跨服務的可靠性最低標準對齊、避免風險在整合時集中爆發。

對應 [SP1 Spotify 平台工程與可靠性契約](/backend/06-reliability/cases/spotify/platform-engineering-and-reliability-contracts/)：揭露三個機制 — reliability contract（每個服務最低要提供什麼）、platform self-service（標準如何降低導入成本）、cross-team evidence（證據如何跨團隊共享）。SP1 case 主場景是內部跨團隊契約、不是 vendor 軸；vendor SLA 治理請見前段「依賴類別」跟 [04.18 operating model](/backend/04-observability/observability-operating-model/) 的 ownership 邊界。

契約讓內部依賴 budget 可以基於 observed reliability（被依賴服務實際的 SLI 觀測值）、補強只靠 vendor SLA 的不足 — 後者通常是上界、不反映實際失效特性。

## 下一步路由

- 6.6 SLO / [error budget](/backend/knowledge-cards/error-budget/)：把依賴可靠性納入目標計算
- 6.8 release gate：把依賴健康度變成放行條件
- 08.15 vendor 事故：第三方事故的事中處理

## 判讀訊號

- 自家服務 SLO 高於依賴 SLA 的乘積、目標不可達
- 第三方 API 退化時無 observed metric、靠用戶投訴發現
- vendor SLA credit 從未請領、無流程
- 新依賴接入無 reliability review
- 關鍵路徑上有「不知道掛了會怎樣」的依賴

## 交接路由

- 04.13 topology：依賴自動發現
- 06.6 SLO：依賴 budget 納入 SLO 算式
- 06.10 contract testing：依賴契約穩定性
- 08.15 vendor 事故：依賴方掛掉的決策模型
