---
title: "Branch Protection"
date: 2026-05-06
description: "說明主線分支如何以規則保護合併與發布前置條件"
tags: ["CI", "branch-protection", "knowledge-card"]
weight: 11
aliases: ["/ci/knowledge-cards/branch-protection/"]
---

Branch Protection 的核心概念是「把主線寫入條件制度化」。它把 [required checks](/devops/ci/knowledge-cards/required-checks/)、review policy 與合併限制集中成 repository gate。

## 跟其他概念的關係

Branch Protection 位在 pull request 與主線分支之間，屬於 [CI](/devops/ci/knowledge-cards/ci-pipeline/) workflow 之外的治理層。

## 可觀察訊號

- 主線偶爾進入未驗證變更。
- workflow 已存在但合併條件未綁定。
- 團隊需要統一 reviewer 與狀態檢查門檻。

## 接近真實服務的例子

專案要求 `md-check` 與 `Playwright tests` 必須綠燈，且至少一位 reviewer 批准才可合併 `main`。

## 判斷條件與後果

Branch Protection 用名稱比對 workflow 回報的 check，所以 workflow 改名而保護規則沒有同步時，規則等待的 check 不會再出現，PR 停在等待狀態而無法合併。審查規則沒有統一時，各 repository 的合併門檻不同，同一類變更在一處要兩人批准、在另一處不用。沒有例外流程時，緊急修復只能用管理員權限繞過保護，繞過的紀錄與理由沒有留下，主線上出現一筆說不出驗證狀態的變更。
