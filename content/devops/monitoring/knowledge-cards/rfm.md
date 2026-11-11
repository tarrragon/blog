---
title: "RFM"
date: 2026-06-19
description: "說明用 Recency / Frequency / Monetary 三個維度把使用者分成可操作群組的分群方法"
weight: 4
tags: ["monitoring", "analytics", "rfm", "knowledge-card"]
aliases: ["/monitoring/knowledge-cards/rfm/"]
---

RFM 的核心概念是「用 Recency（最近活躍度）、Frequency（使用頻率）、Monetary（貢獻價值）三個維度把使用者分成可操作的群組」。每個維度獨立評分後組合，識別出忠實客戶、潛在流失、新使用者、休眠使用者等群組。可先對照 [cohort analysis](/devops/monitoring/knowledge-cards/cohort-analysis/)（按共同特徵分群）和 [funnel analysis](/devops/monitoring/knowledge-cards/funnel-analysis/)（追蹤流程轉換率）。

## 跟其他概念的關係

RFM 位在行為資料累積到一定量之後。它需要每個使用者的 session 歷史（計算 Recency 和 Frequency）和交易歷史（計算 Monetary）。免費產品可以用替代指標取代 Monetary — 產生的內容數量、邀請的使用者數、完成的關鍵操作數。RFM 的前提和 cohort analysis 相同：去識別化（[redaction](/devops/monitoring/knowledge-cards/redaction/)）已完成。

## 可觀察訊號與例子

產品需要 RFM 的訊號是「需要對不同行為模式的使用者採取不同策略」。高 R 高 F 高 M 的忠實客戶需要維護關係，低 R 高 F 高 M 的潛在流失客戶需要挽留，高 R 低 F 低 M 的新使用者需要引導降低入門門檻。

## 判斷條件與後果

每個維度的計算方式決定分出來的群代表什麼。Frequency 的時間窗口比產品正常的使用週期短時，固定但間隔長的使用者被算成低頻；免費產品沒有交易可算 Monetary 時，換成產生的內容數量這類替代指標，「高 M」的意思也跟著換成那個指標。分位數決定 profile 的數量：五等分時三個維度組合出 125 種，多到每一種都對不上一個策略，要歸納成忠實客戶、潛在流失、新使用者這幾個各自對應一種做法的群組；三等分時組合只有 27 種，代價是同一群裡的使用者差異較大。使用者行為改變時群組會變，分群結果只代表計算那一刻的狀態；重新計算的間隔（每週或每月）比行為變化慢時，挽留動作送到的是依上一次分群判定的名單。
