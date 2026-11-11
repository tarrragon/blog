---
title: "Evidence Package"
tags: ["Evidence Package", "Incident Evidence", "證據包"]
date: 2026-05-07
description: "說明觀測、驗證與事故流程如何把證據包成可交接、可回放的 artifact"
weight: 318
---

Evidence package 的核心概念是「把查詢、時間窗、資料品質限制與 owner 打包成可交接證據」。它連接 [log](/backend/knowledge-cards/log/)、[metrics](/backend/knowledge-cards/metrics/)、[trace](/backend/knowledge-cards/trace/) 與 [incident timeline](/backend/knowledge-cards/incident-timeline/)，讓事故與驗證能回放同一組事實。

## 跟其他概念的關係

Evidence package 位在 [dashboard](/backend/knowledge-cards/dashboard/)、[SLI / SLO](/backend/knowledge-cards/sli-slo/) 與 [post-incident review](/backend/knowledge-cards/post-incident-review/) 之間。Dashboard 提供操作視角，SLO 提供判讀門檻，evidence package 保存支撐判斷的來源、時間窗、查詢入口與限制。

## 可觀察訊號與例子

系統需要 evidence package 的訊號是同一段事故證據在交班、release gate 或復盤時反覆被重新查證。常見例子是只保存截圖，下一班 on-call 看得到圖表形狀，卻缺少 query、time range、sampling ratio、ingest delay 與 owner，導致決策背景需要重新建立。

## 判斷條件與後果

Evidence package 的每一個欄位缺席時，接手的人少了一種重建判斷的能力。少了 source、time range 與 query link，下一班 on-call 只看得到截圖裡的圖表形狀，重跑不了同一個查詢；少了 owner，對證據有疑問時找不到可以問的人；少了 data quality 與 confidence，取樣比例或資料延遲造成的偏差看不出來，一張不完整的圖被當成完整的事實；少了 known gap，缺資料的時間段被讀成沒有異常；少了 retention，證據引用的原始資料過期之後，復盤時已經查不回來。這幾項都在時，同一組事實可以直接交給 [incident decision log](/backend/knowledge-cards/incident-decision-log/)、[steady state](/backend/knowledge-cards/steady-state/) 或 [action item closure](/backend/knowledge-cards/action-item-closure/) 使用，不必在交班、release gate 或復盤時重新查證。
