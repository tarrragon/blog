---
title: "4.6 SLI 量測與 SLO 訊號設計"
date: 2026-05-01
description: "把可靠性目標的訊號從 metric 端設計好、餵給 6.6 SLO 政策"
weight: 6
---

## 大綱

- SLI 設計起點：user-journey 而非 system metric
- 量測點選擇：edge / gateway / service / dependency 各自代表什麼
- ratio metric vs latency [percentile](/backend/knowledge-cards/percentile/)：何時用哪種
- [burn rate](/backend/knowledge-cards/burn-rate/) 訊號：multi-window multi-burn-rate alert
- [error budget](/backend/knowledge-cards/error-budget/) 計算所需的 metric 結構
- 跟 [4.2 metrics](/backend/04-observability/metrics-basics/) 的分工：4.2 是 counter/gauge/histogram 基礎、4.6 是 SLI 化的設計
- 跟 [4.4 dashboard-alert](/backend/04-observability/dashboard-alert/) 的分工：4.4 是 alert 規則治理、4.6 是 alert 的訊號源頭
- 反模式：SLI 直接用 system metric、SLO 無 owner、burn rate alert 缺多窗

## 概念定位

SLI 訊號設計是把可靠性目標轉成可量測資料的步驟，責任是讓 SLO 政策建立在使用者旅程與服務結果上。

這一頁處理的是 metric 到 SLI 的轉換。CPU、memory、queue depth 可以提供背景，但 SLI 需要回答使用者是否成功、是否夠快、是否拿到正確結果。

## 核心判讀

判讀 SLI 設計時，先看量測點是否貼近使用者，再看算式是否能穩定支援 error budget。

重點訊號包括：

- edge / gateway / service / dependency 的量測點是否各自有清楚責任
- latency percentile 與 ratio metric 是否對應不同使用者體驗
- [burn rate](/backend/knowledge-cards/burn-rate/) 是否使用多時間窗，避免太吵或太晚
- SLI label 是否有足夠切分能力，同時受 cardinality 預算約束

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
- 06.8 [release gate](/backend/knowledge-cards/release-gate/)：burn rate 觸發 freeze
- 08.1 [incident severity](/backend/knowledge-cards/incident-severity/)：burn rate 對應 severity 門檻
- 04.14 anomaly detection：跟 SLO threshold 的訊號分工
