---
title: "Rollback Strategy"
tags: ["回滾策略", "Rollback Strategy"]
date: 2026-04-23
description: "說明事故期間如何判斷回滾、回切與暫停變更"
weight: 156
---

Rollback strategy 的核心概念是「在事故期間用可驗證條件決定是否回滾」。回滾是根據影響面、資料風險與回復速度做出的風險控制決策，當成預設答案會忽略回滾本身的代價。 可先對照 [Incident Severity](/backend/knowledge-cards/incident-severity/)。

## 跟其他概念的關係

回滾策略連接 [incident severity](/backend/knowledge-cards/incident-severity/)、[blast radius](/backend/knowledge-cards/blast-radius/)、[cutover / switchover](/backend/knowledge-cards/cutover-switchover/) 與 [fallback plan](/backend/knowledge-cards/fallback-plan/)；是否放行變更則會受 [Release Gate](/backend/knowledge-cards/release-gate/) 影響，而實際可行性則應由 [Rollback Rehearsal](/backend/knowledge-cards/rollback-rehearsal/) 驗證。

## 可觀察訊號與例子

系統需要 rollback strategy 的訊號是新版本上線後出現錯誤率上升。若回滾可在 5 分鐘內顯著降低使用者影響，通常優先回滾，再在低風險環境分析根因。

## 判斷條件與後果

回滾的判斷對象是在這次變更與這個時點，回滾能否比其他做法更快降低影響。新舊版本的資料格式相容、回滾能在幾分鐘內降低錯誤率時，先回滾、再在低風險環境分析根因；新版本已經寫入舊版本讀不懂的資料時，回滾讓舊版本讀到它不認得的格式，變成第二起事故，所以觸發條件之外另有資料相容性檢查。回滾本身也可能失敗或沒有改善，沒有停止條件與回滾後驗證時，團隊無從判斷回滾是否有效、何時改走其他路線。高風險變更的回滾步驟沒有在發版前演練過時，步驟不可行要到事故當下才被發現。
