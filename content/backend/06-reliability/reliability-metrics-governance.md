---
title: "6.18 Reliability Metrics Governance"
date: 2026-05-01
description: "DORA / SPACE / CFR 等可靠性指標的選用、量測與治理"
weight: 18
---

## 大綱

- 為何指標需要治理：選錯指標會優化錯方向、Goodhart's law 風險
- DORA 四指標：deploy frequency、lead time、change failure rate、[MTTR](/backend/knowledge-cards/mttr/)
- SPACE：Satisfaction、Performance、Activity、Communication、Efficiency 補 DORA 缺的人因
- 指標選用：團隊發展階段不同、指標重點不同（startup / scale / mature）
- baseline 對齊：跟同產業 / 同團隊大小對標、不是抄業界數字
- 反 gaming：指標被優化到失去意義時的偵測（如 deploy 拆碎只為衝頻率）
- 跟 [6.6 SLO](/backend/06-reliability/slo-error-budget/) 的差異：SLO 是商業承諾、6.18 是工程能力
- 跟 [6.8 release gate](/backend/06-reliability/release-gate/) 的整合：CFR 是 gate 健康度
- 反模式：指標當 KPI 強制達成、團隊 gaming；只看 4 指標忽略品質；指標跨團隊比較強制排名

## 概念定位

Reliability metrics governance 是治理指標選擇、量測與解讀方式的流程，責任是確保團隊不是在追一組漂亮但失真的數字。

這一頁關心的是哪個指標代表真正的可靠性。沒有 governance，指標會先被報表化，再被目標化，最後失去判讀能力。

## 核心判讀

判讀 metrics 時，先看指標是否對準使用者感受，再看它是否能驅動工程決策。

重點訊號包括：

- SLI 是否有明確觀測窗口與採樣邊界
- SLO 是否能轉成 release / alert / incident 決策
- DORA / SPACE / CFR 是否被混用成單一成績單
- metric drift 是否被記錄與校正

## 案例對照

- [Google](/backend/06-reliability/cases/google/_index.md)：SRE 指標治理的典型參考。
- [Honeycomb](/backend/06-reliability/cases/honeycomb/_index.md)：觀測資料的判讀方式本身就是產品責任。
- [Datadog](/backend/08-incident-response/cases/datadog/_index.md)：指標平台若不治理，會反向影響事故判讀。

## 下一步路由

- 6.6 SLO / error budget：把指標變成政策
- 08.11 observability / reliability / incident loop：把治理回寫到三模組閉環
- 08.5 [post-incident review](/backend/knowledge-cards/post-incident-review/)：指標漂移通常先在復盤裡被看見

## 判讀訊號

- 工程團隊優化指標數字、實際品質下降
- 指標數字好看、客戶投訴與事故未減
- 跨團隊強制排名、團隊間互不分享經驗
- DORA 採集靠人工、指標滯後一個月以上
- 指標無 owner、半年無人 review

## 交接路由

- 06.6 SLO：商業承諾層的指標
- 06.8 release gate：CFR 是 gate 健康度訊號
- 04.6 SLI/SLO：跟訊號層的對應
- 08.5 [post-incident review](/backend/knowledge-cards/post-incident-review/)：[MTTR](/backend/knowledge-cards/mttr/) 計算的事件來源
