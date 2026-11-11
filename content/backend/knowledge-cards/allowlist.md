---
title: "Allowlist"
tags: ["允許清單", "Policy Control"]
date: 2026-04-30
description: "說明如何用明確允許條件控制例外放行範圍"
weight: 258
---

Allowlist 的核心概念是「以明確條件列出可放行項目，讓例外放行保持可控邊界」。它把放行決策從口頭同意轉成可稽核政策。 可先對照 [Input Validation](/backend/knowledge-cards/input-validation/)。

## 跟其他概念的關係

Allowlist 位在 [Input Validation](/backend/knowledge-cards/input-validation/)、[Release Freeze](/backend/knowledge-cards/release-freeze/) 與 [Authorization](/backend/knowledge-cards/authorization/) 之間。它可以同時用於請求治理、變更治理與資源治理。

## 可觀察訊號

系統需要 allowlist 的訊號是：

- 需要在凍結期間保留少量必要變更
- 高風險操作需要先符合條件才能執行
- 團隊需要限制可用來源、版本或操作集合
- 放行規則需要可追蹤與可回顧

## 接近真實網路服務的例子

release freeze 期間，只允許安全修補版本與回復工具變更進入正式環境；資料匯出流程只允許特定角色與核准任務編號觸發。

## 判斷條件與後果

Allowlist 的每個欄位各擋住一種放行失控。允許對象與限制條件寫得不清楚時，放行範圍由執行的人當下解讀；沒有有效期限時，為凍結期開的例外在凍結結束後仍然生效，例外變成常態；沒有審查者時，項目加進清單不經第二個人確認；沒有撤銷機制時，發現放錯了也收不回來。放行條件只存在於人工記憶時（「這個版本上次有人同意過」），稽核時查不到當初的依據，所以條件寫成系統驗證得了的形式，例如 release freeze 期間的版本類型、資料匯出流程的角色與核准任務編號。
