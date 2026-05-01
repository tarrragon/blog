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

## 判讀訊號

- CI 時長 > 30 min、PR 等 CI 變排隊 bottleneck
- fast / slow 沒分層、單一 PR 卡所有測試
- 測試 flaky 率高、retry 變常態、訊號被噪音吞掉
- artifact 從 source 重複 rebuild、無 cache
- env var 跨環境寫死 / 互相污染、staging 跟 prod 行為不同

## 交接路由

- 06.10 contract testing：契約驗證作為 CI stage
- 06.13 perf regression gate：效能 baseline 持續對齊
- 06.16 test data：fixture / seed 跟 CI 階段的耦合
