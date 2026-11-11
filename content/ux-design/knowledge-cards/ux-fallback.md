---
title: "Fallback（UX）"
date: 2026-06-19
description: "說明 gate 未通過時使用者的替代路徑，和 backend fallback（server-side 降級）的語意區別"
weight: 3
tags: ["ux-design", "knowledge-card", "fallback", "gate"]
---

UX fallback 的核心概念是「gate 未通過時使用者的替代路徑」。替代路徑可以是替代驗證方式（密碼代替 Face ID）、降級功能（部分功能可用）、手動重試、或放棄操作返回上一頁。和 [Fallback（Backend）](/backend/knowledge-cards/fallback/) 不同，UX fallback 關注的是使用者體驗層的路徑設計，而非 server-side 的服務降級策略。可先對照 [Gate](/ux-design/knowledge-cards/gate/)。

## 跟其他概念的關係

UX fallback 位在 [Gate](/ux-design/knowledge-cards/gate/) 設計的失敗路徑中。Gate 的三問（成功/失敗/不確定）中，失敗路徑的具體內容就是 UX fallback。Backend 的 [fallback](/backend/knowledge-cards/fallback/) 是系統在依賴失敗時用替代結果維持服務，UX fallback 是使用者在 gate 失敗時的操作替代方案。兩者可能並存 — server-side fallback 提供降級資料，UX fallback 決定如何呈現這些降級資料給使用者。

## 可觀察訊號與例子

需要 UX fallback 的訊號是 gate 失敗時使用者完全無法繼續。常見情境：biometric 設定 `biometricOnly: true` 導致 Face ID 失敗時沒有密碼 fallback、error 畫面只有重試按鈕沒有返回按鈕、網路斷線後所有功能不可用但部分功能不依賴網路。

## 判斷條件與後果

提供哪一種 fallback，取決於安全需求和使用場景之間的取捨。安全需求高的場景（銀行 app）提供低安全等級的 fallback 時，強驗證可以被較弱的那一條路繞過，所以這類 app 可能只留重試或返回；自用工具的使用者就是 owner，密碼 fallback 帶來的風險低，換到的是 Face ID 失敗時仍然進得去。這個取捨沒有寫進功能規格時，它由實作時的設定值隱含決定，例如 `biometricOnly: true` 讓 Face ID 失敗後沒有密碼可用。gate 失敗的狀態連同它的 fallback 列進[畫面狀態矩陣](/ux-design/knowledge-cards/screen-state-matrix/)的退出路徑欄時，矩陣檢查得到使用者在 gate 失敗之後是否有出口。
