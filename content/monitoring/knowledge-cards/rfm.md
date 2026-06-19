---
title: "RFM"
date: 2026-06-19
description: "說明用 Recency / Frequency / Monetary 三個維度把使用者分成可操作群組的分群方法"
weight: 4
tags: ["monitoring", "analytics", "rfm", "knowledge-card"]
---

RFM 的核心概念是「用 Recency（最近活躍度）、Frequency（使用頻率）、Monetary（貢獻價值）三個維度把使用者分成可操作的群組」。每個維度獨立評分後組合，識別出忠實客戶、潛在流失、新使用者、休眠使用者等群組。可先對照 [cohort analysis](/monitoring/knowledge-cards/cohort-analysis/)（按共同特徵分群）和 [funnel analysis](/monitoring/knowledge-cards/funnel-analysis/)（追蹤流程轉換率）。

## 概念位置

RFM 位在行為資料累積到一定量之後。它需要每個使用者的 session 歷史（計算 Recency 和 Frequency）和交易歷史（計算 Monetary）。免費產品可以用替代指標取代 Monetary — 產生的內容數量、邀請的使用者數、完成的關鍵操作數。RFM 的前提和 cohort analysis 相同：去識別化（[redaction](/monitoring/knowledge-cards/redaction/)）已完成。

## 可觀察訊號與例子

產品需要 RFM 的訊號是「需要對不同行為模式的使用者採取不同策略」。高 R 高 F 高 M 的忠實客戶需要維護關係，低 R 高 F 高 M 的潛在流失客戶需要挽留，高 R 低 F 低 M 的新使用者需要引導降低入門門檻。

## 設計責任

RFM 要定義每個維度的計算方式（Recency 用天數還是週數、Frequency 的時間窗口多長、Monetary 用什麼指標）、分位數（五等分還是三等分）、群組歸納（125 種 profile 歸納成幾個可操作群組）、以及重新計算的頻率（每週還是每月）。分群結果是動態的 — 使用者行為改變時群組會變。
