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

## 概念定位

Performance regression gate 是把效能 baseline 轉成持續放行條件，責任是避免看似功能正確的變更悄悄拖垮延遲、吞吐或成本。

這一頁關心的是變更有沒有偷走系統的效能餘裕。沒有 gate，效能退化常常要等使用者先感受到才會被看見。

## 核心判讀

判讀效能 gate 時，先看 baseline 是否穩定，再看 regression 是否足夠敏感。

重點訊號包括：

- baseline 是否來自 production-like workload
- regression 是否能分辨 noise 與真實退化
- perf budget 是否跟 release gate 綁定
- 當退化出現時，是否能快速定位到 code path 或依賴

## 案例對照

- [Google](/backend/06-reliability/cases/google/_index.md)：大型系統需要把效能回饋變成日常 gate。
- [LinkedIn](/backend/06-reliability/cases/linkedin/_index.md)：高互動平台的 latency regression 不能只靠事後觀察。
- [Shopify](/backend/06-reliability/cases/shopify/_index.md)：高峰流量下，效能退化等於可靠性退化。

## 下一步路由

- 06.2 load testing：baseline 來自哪種 workload
- 06.8 release gate：perf budget 如何納入放行
- 06.9 capacity / cost：效能退化常伴隨成本上升

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
