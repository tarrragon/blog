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
