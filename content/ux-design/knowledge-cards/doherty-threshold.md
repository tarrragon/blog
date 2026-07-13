---
title: "Doherty Threshold（400ms 門檻）"
date: 2026-07-13
description: "說明 400ms 回應時間門檻的出身（IBM 生產力研究）、現代設計慣例的轉譯過程，以及它跟 Nielsen 感知門檻的量測差異"
weight: 5
tags: ["ux-design", "knowledge-card", "interaction-feedback", "response-time"]
---

Doherty Threshold 的核心概念是「系統回應時間低於 400ms 時，人機互動進入雙方都不需要等待對方的流暢循環」。出自 Doherty 與 Thadani 1982 年的 IBM 技術報告，原始量測對象是操作生產力 — 回應時間壓到 400ms 以下時，使用者完成任務的效率大幅提升。它跟 [Debounce](/ux-design/knowledge-cards/debounce/) 同屬互動回饋的時間參數：前者管輸出速度的門檻、後者管重複輸入的收斂。

## 概念位置

介面回應時間的研究有兩套量尺：Nielsen 的 100ms / 1s / 10s 量的是主觀感知與注意力（什麼時候「覺得慢」、什麼時候放棄），Doherty 的 400ms 量的是客觀生產力（什麼時候做事變快）。現代設計整理（Laws of UX 等）把 400ms 轉譯成回饋規則「400ms 內完成的操作可省略 loading 指示」— 這是從原始研究衍生的設計慣例，引用時要區分研究結論與慣例轉譯。

## 可觀察訊號與例子

400ms 門檻的典型應用是判斷「這個操作要不要顯示 loading」：本地資料庫查詢、快速 API 回應這類多數落在 400ms 內的操作，加 spinner 反而製造閃爍；延遲顯示（發請求後等 300-400ms 才掛 spinner）就是把這個門檻做成機制。

## 設計責任

引用這個門檻的設計責任是對齊延遲的真實分布 — 平均 300ms 不代表每次都在 400ms 內，對表要用 p90 / p95。完整的門檻推導與落地策略見[時間感知與回應策略](/ux-design/06-interaction-feedback/response-time-strategy/)。
