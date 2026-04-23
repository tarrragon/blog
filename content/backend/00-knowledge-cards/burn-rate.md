---
title: "Burn Rate"
date: 2026-04-23
description: "說明 error budget 消耗速度如何支援告警與事故分級"
weight: 102
---

Burn rate 的核心概念是「error budget 被消耗的速度」。它讓團隊知道目前錯誤率若持續下去，多久會耗盡可靠性預算。

## 概念位置

Burn rate 是 SLO alerting 的常用方式。短時間高 burn rate 代表急性事故；長時間中等 burn rate 代表慢性可靠性退化。

## 可觀察訊號與例子

系統需要 burn rate 的訊號是錯誤率需要轉成行動優先級。付款服務 10 分鐘內大量失敗需要立即處理；搜尋服務一天內慢慢超標則可能需要容量與查詢優化。

## 設計責任

Burn rate 告警要設定多時間窗，兼顧快速事故與慢性消耗。Runbook 應說明不同 burn rate 對應的升級與緩解流程。
