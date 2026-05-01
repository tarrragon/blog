---
title: "6.6 SLO 與 Error Budget 政策"
date: 2026-05-01
description: "把可靠性目標轉成可驗證量測與凍結條件"
weight: 6
---

## 大綱

- SLI 選型：user-journey-centric vs system-metric
- SLO 目標訂定：可達性、商業意義、頻率窗
- error budget：burn rate、policy、freeze 條件
- 跟 [04 觀測](/backend/04-observability/) 的訊號交接
- 跟 [6.8 release gate](/backend/06-reliability/release-gate/) 的凍結觸發
- 跟 [8.1 事故分級](/backend/08-incident-response/incident-severity-trigger/) 的門檻對齊
- 反模式：cargo-cult 99.99%、SLO 無人擁有、burn rate 無 alert

## 判讀訊號

- SLO 數字無 owner、過半年沒檢視
- burn rate 無 alert、只有 monthly review
- error budget 耗盡但 deployment 節奏不變
- SLI 用 system metric（CPU / memory）、不對應 user journey
- 目標數字是抄來的（99.9 / 99.99）、無商業 anchor

## 交接路由

- 04 訊號治理：SLI / burn rate metric 設計
- 06.8 release gate：error budget 耗盡觸發 freeze
- 06.9 capacity / cost：容量不足傳導為 SLO 風險
- 06.14 dependency budget：依賴可靠性納入 SLO 算式
- 08 事故閉環：burn rate alert 啟動條件
- 08.13 repeated / toil：error budget 撥用 toil reduction
- 06.18 reliability metrics：SLO 跟 DORA / SPACE 的指標分層
