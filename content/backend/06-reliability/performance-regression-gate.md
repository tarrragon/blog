---
title: "6.13 Performance Regression Gate"
date: 2026-05-01
description: "把效能 baseline 從一次性壓測變成持續對齊的 release gate"
weight: 13
---

## 大綱

- 跟 [6.2 load test](/backend/06-reliability/load-testing/) 的差異：6.2 訂 baseline、6.13 確保 baseline 不被偷走
- 持續性能驗證的定位：每次 PR / canary 對齊歷史 baseline
- micro benchmark vs end-to-end perf test 的取捨
- variance 控制：硬體 / 鄰居 / network 噪音的去除
- regression 判讀：絕對門檻 vs 相對退化 vs 統計顯著性
- 跟 [4.9 continuous profiling](/backend/04-observability/continuous-profiling/) 的整合：profile diff 作為退化定位
- 跟 [6.8 release gate](/backend/06-reliability/release-gate/) 的整合：perf 退化作為 gate 條件
- 反模式：perf test 只在 release 前跑一次、退化已累積；CI 用 shared runner 噪音吞掉訊號；只看平均不看 percentile

## 判讀訊號

- 連續多版微小退化、累積後才被發現
- 大版本升級 latency 漲、定位到具體 commit 困難
- benchmark variance > 退化幅度、訊號被噪音吞掉
- canary 只看 error rate、不看 latency / throughput
- 第三方依賴（DB / cache）效能變化未納入 baseline

## 交接路由

- 04.9 continuous profiling：退化定位到 callstack
- 05 部署：canary 階段的 perf gate
- 06.2 load test：baseline 來源
- 06.8 release gate：退化觸發 freeze
- 06.17 feature flag：flag 切換後的效能驗證
