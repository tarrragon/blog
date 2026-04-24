---
title: "Rollback Strategy"
date: 2026-04-23
description: "說明事故期間如何判斷回滾、回切與暫停變更"
weight: 155
---

Rollback strategy 的核心概念是「在事故期間用可驗證條件決定是否回滾」。回滾不是預設答案，而是根據影響面、資料風險與回復速度做出的風險控制決策。

## 概念位置

回滾策略連接 [incident severity](../incident-severity/)、[blast radius](../blast-radius/)、[cutover / switchover](../cutover-switchover/) 與 [fallback plan](../fallback-plan/)；是否放行變更則會受 [Release Gate](release-gate/) 影響，而實際可行性則應由 [Rollback Rehearsal](rollback-rehearsal/) 驗證。

## 可觀察訊號與例子

系統需要 rollback strategy 的訊號是新版本上線後出現錯誤率上升。若回滾可在 5 分鐘內顯著降低使用者影響，通常優先回滾，再在低風險環境分析根因。

## 設計責任

回滾策略要定義觸發條件、資料相容性檢查、回滾步驟、停止條件與回滾後驗證。高風險變更應在發版前先演練回滾流程。

## 英文術語對照
- Rollback strategy
- Rollback plan
