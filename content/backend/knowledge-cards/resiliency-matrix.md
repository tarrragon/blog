---
title: "Resiliency Matrix"
tags: ["Resiliency Matrix", "Failure Mode", "Game Day", "可靠性"]
date: 2026-06-23
description: "服務與失敗模式的交叉矩陣，標記每個交叉點的防護狀態與驗證覆蓋"
weight: 322
---

Resiliency matrix 的核心概念是「用 service × failure mode 的交叉矩陣，把系統的防護狀態從隱性假設變成可檢查資產」。每個交叉點標記 covered（有防護且已驗證）、gap（已知缺口待補）或 in-progress（防護建置中），讓團隊能系統性地追蹤 [blast radius](/backend/knowledge-cards/blast-radius/) 覆蓋。

## 跟其他概念的關係

Resiliency matrix 位在 [blast radius](/backend/knowledge-cards/blast-radius/) 與 [readiness](/backend/knowledge-cards/readiness/) 之間。它把失敗模式盤點（FMEA / pre-mortem）的產出結構化成可追蹤矩陣，並驅動 [game day](/backend/knowledge-cards/game-day/) 演練題目的選擇 — gap 欄直接成為演練的優先目標。

## 可觀察訊號與例子

需要 resiliency matrix 的訊號是團隊知道有風險但不確定哪些已有防護。典型例子是高峰活動前的準備流程：把所有關鍵服務列成行、所有失敗模式（依賴斷線 / 容量超限 / 資料污染 / 配置漂移）列成列，逐格檢查防護狀態。Shopify 在 BFCM 準備中使用這個工具把年度驗證進度視覺化。

## 判斷條件與後果

Resiliency matrix 的判斷對象是每一格的狀態是否還反映現在的系統。每次演練後都更新 gap 與 covered 時，matrix 是一份可排序、可追蹤的 reliability debt 清單，gap 欄直接成為下一次 game day 的題目，維護節奏可以跟 [6.21 reliability debt backlog](/backend/06-reliability/reliability-debt-backlog/) 對齊。超過 6 個月沒有更新、或 gap 沒有 owner 時，標成 covered 的格子可能已經因為架構變動而失效，團隊照 matrix 判斷的是過去的防護狀態，這是治理失敗的訊號。新上線的服務與新發現的失敗模式沒有加進列與欄時，它們的缺口連 gap 都標不出來，所以每季檢查一次 matrix 的完整性。
