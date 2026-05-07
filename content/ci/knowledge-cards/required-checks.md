---
title: "Required Checks"
date: 2026-05-06
description: "說明 pull request 的必要檢查如何作為合併 gate"
tags: ["CI", "required-checks", "knowledge-card"]
weight: 3
---

Required Checks 的核心概念是「把合併條件綁定到檢查結果」。它讓主線保護不依賴人工記憶，而依賴可觀測狀態。

## 概念位置

Required Checks 位在 repository branch protection，連接 pull request 與 CI workflow 結果。

## 可觀察訊號

- PR 是否可合併取決於特定 checks 狀態。
- 團隊需要確保高風險變更不繞過驗證。
- CI workflow 增刪後需要同步調整合併條件。

## 接近真實服務的例子

專案可要求 `md-check` 與 `Playwright tests` 都通過才能合併 `main`。若只跑 workflow 但未設為 required，主線仍可能進入紅燈變更。

## 設計責任

Required Checks 要定義必要檢查集合、擁有者與變更流程，並和 workflow 命名保持一致。
