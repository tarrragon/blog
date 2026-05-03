---
title: "6.14 Dependency Reliability Budget"
date: 2026-05-01
description: "把內外依賴的可靠性納入 SLO 計算與設計約束"
weight: 14
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

## 下一步路由

- 6.6 SLO / error budget：把依賴可靠性納入目標計算
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
