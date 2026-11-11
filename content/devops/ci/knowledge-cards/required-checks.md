---
title: "Required Checks"
date: 2026-05-06
description: "說明 pull request 的必要檢查如何作為合併 gate"
tags: ["CI", "required-checks", "knowledge-card"]
weight: 3
aliases: ["/ci/knowledge-cards/required-checks/"]
---

Required Checks 的核心概念是「把合併條件綁定到檢查結果」。它讓[主線保護](/devops/ci/knowledge-cards/branch-protection/)不依賴人工記憶，而依賴可觀測狀態。

## 跟其他概念的關係

Required Checks 位在 repository branch protection，連接 pull request 與 [CI](/devops/ci/knowledge-cards/ci-pipeline/) workflow 結果。

## 可觀察訊號

- PR 是否可合併取決於特定 checks 狀態。
- 團隊需要確保高風險變更不繞過驗證。
- CI workflow 增刪後需要同步調整合併條件。

## 接近真實服務的例子

專案可要求 `md-check` 與 `Playwright tests` 都通過才能合併 `main`。若只跑 workflow 但未設為 required，主線仍可能進入紅燈變更。

## 判斷條件與後果

Required Checks 用 check 的名稱比對狀態，所以合併條件列的名稱跟 workflow 實際產出的 check 名稱是否對得上，決定這道關卡是否發揮作用。workflow 改名或拆分之後，branch protection 仍要求舊名稱的 check 時，PR 一直等待一個不會再出現的狀態而無法合併；新增的 workflow 沒有被設為 required 時，它跑出紅燈也不擋合併，主線仍可能進入紅燈變更。必要檢查集合沒有 owner 與變更流程時，這兩種落差要等 PR 卡住或主線變紅之後才被發現。
