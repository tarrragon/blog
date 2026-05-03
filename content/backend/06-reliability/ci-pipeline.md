---
title: "6.1 CI pipeline"
date: 2026-04-23
description: "整理分層測試、快慢測試與 artifact 管理"
weight: 1
---

## 大綱

- test stages
- fast/slow split
- artifact
- environment variables

## 概念定位

CI pipeline 是可靠性的第一道過濾器，責任是把快速回饋、慢速驗證與可重現產物切成不同層，讓每次變更都能在一致條件下被判讀。

這一層關心的是「變更能不能被穩定驗證」，不是單純把測試跑完。pipeline 的價值在於分層、隔離與可追蹤，讓 flaky 訊號不會直接污染放行判斷。

## 核心判讀

CI 的健康度先看回饋節奏，再看訊號品質。fast path 應該覆蓋最常見的破壞面，slow path 負責深層驗證，artifact 則要能從同一份輸入重播。

判讀時先看四件事：

- stage 是否按成本與風險分層
- artifact 是否重用，不是每次從 source 重建
- environment variables 是否封裝，避免跨環境漂移
- flaky test 是否有治理路徑，而不是只靠 retry

## 案例對照

- [Google](/backend/06-reliability/cases/google/_index.md)：把 fast/slow 分層做成常態工程習慣，讓大規模變更仍能維持回饋速度。
- [LinkedIn](/backend/06-reliability/cases/linkedin/_index.md)：CI 不只驗證功能，也用來承接 load / perf 類回饋。
- [Stripe](/backend/06-reliability/cases/stripe/_index.md)：把放行節奏和變更風險綁在一起，避免小改動帶出大事故。

## 下一步路由

- 06.10 contract testing：把跨服務契約納入 CI stage
- 06.13 perf regression gate：把效能回饋變成 gate
- 06.16 test data：把 fixture / seed 納入 pipeline 管理

## 判讀訊號

- CI 時長 > 30 min、PR 等 CI 變排隊 bottleneck
- fast / slow 沒分層、單一 PR 卡所有測試
- 測試 flaky 率高、retry 變常態、訊號被噪音吞掉
- artifact 從 source 重複 rebuild、無 cache
- env var 跨環境寫死 / 互相污染、staging 跟 prod 行為不同
