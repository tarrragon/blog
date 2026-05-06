---
title: "Toil"
tags: ["Toil", "重複手動工作"]
date: 2026-05-02
description: "說明重複、手動、無永久價值的工作如何成為工程治理對象"
weight: 315
---


Toil 的核心概念是「重複、手動、無永久價值、可自動化的工作」。它通常和 [on-call](/backend/knowledge-cards/on-call/) 壓力、[alert fatigue](/backend/knowledge-cards/alert-fatigue/) 與 [runbook](/backend/knowledge-cards/runbook/) 綁在一起。

## 概念位置

Toil 位在 [alert-fatigue](/backend/knowledge-cards/alert-fatigue/)、[runbook](/backend/knowledge-cards/runbook/) 與 [post-incident-review](/backend/knowledge-cards/post-incident-review/) 之間。它把反覆出現的手動修復工作，轉成能被自動化或系統性消除的治理對象。

## 可觀察訊號與例子

系統需要 toil 治理的訊號是值班時間被重複修復工作吃掉，且每次事故後都只是多一個手動步驟。常見例子包括固定重啟、手動 replay、人工清 queue、或每週都要補同一份報表。

## 設計責任

Toil 治理要定義可自動化優先序、移除條件、owner 與替代路徑。它的目標不是把所有手工流程都消滅，而是把沒有長期價值的重複成本逐步壓下來。
