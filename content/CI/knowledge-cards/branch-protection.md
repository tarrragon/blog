---
title: "Branch Protection"
date: 2026-05-06
description: "說明主線分支如何以規則保護合併與發布前置條件"
tags: ["CI", "branch-protection", "knowledge-card"]
weight: 11
---

Branch Protection 的核心概念是「把主線寫入條件制度化」。它把 required checks、review policy 與合併限制集中成 repository gate。

## 概念位置

Branch Protection 位在 pull request 與主線分支之間，屬於 CI workflow 之外的治理層。

## 可觀察訊號

- 主線偶爾進入未驗證變更。
- workflow 已存在但合併條件未綁定。
- 團隊需要統一 reviewer 與狀態檢查門檻。

## 接近真實服務的例子

專案要求 `md-check` 與 `Playwright tests` 必須綠燈，且至少一位 reviewer 批准才可合併 `main`。

## 設計責任

Branch Protection 要定義必要 checks、審查規則與例外流程，並和 workflow 命名同步維護。
