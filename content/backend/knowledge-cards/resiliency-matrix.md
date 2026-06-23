---
title: "Resiliency Matrix"
tags: ["Resiliency Matrix", "Failure Mode", "Game Day", "可靠性"]
date: 2026-06-23
description: "服務與失敗模式的交叉矩陣，標記每個交叉點的防護狀態與驗證覆蓋"
weight: 321
---

Resiliency matrix 的核心概念是「用 service × failure mode 的交叉矩陣，把系統的防護狀態從隱性假設變成可檢查資產」。每個交叉點標記 covered（有防護且已驗證）、gap（已知缺口待補）或 in-progress（防護建置中），讓團隊能系統性地追蹤 [blast radius](/backend/knowledge-cards/blast-radius/) 覆蓋。

## 概念位置

Resiliency matrix 位在 [blast radius](/backend/knowledge-cards/blast-radius/) 與 [readiness](/backend/knowledge-cards/readiness/) 之間。它把失敗模式盤點（FMEA / pre-mortem）的產出結構化成可追蹤矩陣，並驅動 [game day](/backend/knowledge-cards/game-day/) 演練題目的選擇 — gap 欄直接成為演練的優先目標。

## 可觀察訊號與例子

需要 resiliency matrix 的訊號是團隊知道有風險但不確定哪些已有防護。典型例子是高峰活動前的準備流程：把所有關鍵服務列成行、所有失敗模式（依賴斷線 / 容量超限 / 資料污染 / 配置漂移）列成列，逐格檢查防護狀態。Shopify 在 BFCM 準備中使用這個工具把年度驗證進度視覺化。

## 設計責任

Resiliency matrix 的責任是把 reliability debt 從模糊的「我們知道有缺口」變成可排序、可追蹤的清單。它的維護節奏跟 [6.21 reliability debt backlog](/backend/06-reliability/reliability-debt-backlog/) 對齊 — 每次演練後更新 matrix 的 gap/covered 狀態，每季 review matrix 的完整性。matrix 變成文件而不是工具（超過 6 個月未更新、gap 無 owner）是治理失敗的訊號。
