---
title: "4.6 SLI 量測與 SLO 訊號設計"
date: 2026-05-01
description: "把可靠性目標的訊號從 metric 端設計好、餵給 6.6 SLO 政策"
weight: 6
---

## 大綱

- SLI 設計起點：user-journey 而非 system metric
- 量測點選擇：edge / gateway / service / dependency 各自代表什麼
- ratio metric vs latency percentile：何時用哪種
- burn rate 訊號：multi-window multi-burn-rate alert
- error budget 計算所需的 metric 結構
- 跟 [4.2 metrics](/backend/04-observability/metrics-basics/) 的分工：4.2 是 counter/gauge/histogram 基礎、4.6 是 SLI 化的設計
- 跟 [4.4 dashboard-alert](/backend/04-observability/dashboard-alert/) 的分工：4.4 是 alert 規則治理、4.6 是 alert 的訊號源頭
- 反模式：SLI 直接用 system metric、SLO 無 owner、burn rate alert 缺多窗

## 判讀訊號

- alert 用 system metric（CPU / memory）而非 user-facing 訊號
- burn rate 只有單窗、噪音多 / 太晚
- SLI 計算用平均、不用 percentile
- error budget 算式分母不穩（流量低時誤觸發 / 高時稀釋）
- SLI 量測點離 user 太遠（內部 service 而非 edge）

## 交接路由

- 04.7 cardinality / cost：SLI metric 的 cardinality 預算
- 04.10 client-side / RUM：user-journey-centric SLI 的訊號來源
- 06.6 SLO 政策：error budget 餘額作為 freeze 條件
- 06.8 release gate：burn rate 觸發 freeze
- 08.1 事故分級：burn rate 對應 severity 門檻
- 04.14 anomaly detection：跟 SLO threshold 的訊號分工
