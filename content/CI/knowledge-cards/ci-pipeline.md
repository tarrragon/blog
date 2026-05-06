---
title: "CI Pipeline"
date: 2026-05-06
description: "說明持續整合如何在合併前自動驗證變更品質與相容性"
tags: ["CI", "pipeline", "knowledge-card"]
weight: 1
---

CI Pipeline 的核心概念是「在合併前自動驗證變更」。它把品質門檻前移，讓問題在進主線前被發現。

## 概念位置

CI Pipeline 位在開發提交、pull request 與主線保護之間，常由 lint、test、build、security check 組成。

## 可觀察訊號

- PR 需要依賴檢查結果決定能否合併。
- 團隊需要一致的失敗判讀入口。
- 本機通過但共享流程失敗時，需要明確定位差異。

## 接近真實服務的例子

前端專案會把 markdown lint、browser test 與 production build 放在同一套 CI 驗證入口。後端專案則可能加入 contract test、migration check 或 image scan。

## 設計責任

CI Pipeline 要定義必跑檢查、失敗回饋路由與執行時間上限，讓綠燈具備可發布前提。
