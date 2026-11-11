---
title: "CI Pipeline"
date: 2026-05-06
description: "說明持續整合如何在合併前自動驗證變更品質與相容性"
tags: ["CI", "pipeline", "knowledge-card"]
weight: 1
aliases: ["/ci/knowledge-cards/ci-pipeline/"]
---

CI Pipeline 的核心概念是「在合併前自動驗證變更」，驗證通過後交由 [CD Pipeline](/devops/ci/knowledge-cards/cd-pipeline/) 接手部署。它把品質門檻前移，讓問題在進主線前被發現。

## 跟其他概念的關係

CI Pipeline 位在開發提交、pull request 與[主線保護](/devops/ci/knowledge-cards/branch-protection/)之間，常由 lint、test、build、security check 組成。

## 可觀察訊號

- PR 需要依賴檢查結果決定能否合併。
- 團隊需要一致的失敗判讀入口。
- 本機通過但共享流程失敗時，需要明確定位差異。

## 接近真實服務的例子

前端專案會把 markdown lint、browser test 與 production build 放在同一套 CI 驗證入口。後端專案則可能加入 contract test、migration check 或 image scan。

## 判斷條件與後果

CI Pipeline 的綠燈代表變更可以合併，這個代表成立與否取決於三項設定。必跑檢查沒有固定時，綠燈只說明這次剛好跑了的那幾項通過，沒跑的項目要到主線上才失敗；失敗回饋沒有統一的路由時，各項檢查的錯誤散在不同的 log，提交者看不出失敗的是哪一項、原因是什麼；執行時間沒有上限時，一個卡住的 job 讓 PR 一直停在等待狀態，直到有人手動取消。
