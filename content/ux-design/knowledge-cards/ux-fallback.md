---
title: "Fallback（UX）"
date: 2026-06-19
description: "說明 gate 未通過時使用者的替代路徑，和 backend fallback（server-side 降級）的語意區別"
weight: 3
tags: ["ux-design", "knowledge-card", "fallback", "gate"]
---

UX fallback 的核心概念是「gate 未通過時使用者的替代路徑」。替代路徑可以是替代驗證方式（密碼代替 Face ID）、降級功能（部分功能可用）、手動重試、或放棄操作返回上一頁。和 [Fallback（Backend）](/backend/knowledge-cards/fallback/) 不同，UX fallback 關注的是使用者體驗層的路徑設計，而非 server-side 的服務降級策略。可先對照 [Gate](/ux-design/knowledge-cards/gate/)。

## 概念位置

UX fallback 位在 [Gate](/ux-design/knowledge-cards/gate/) 設計的失敗路徑中。Gate 的三問（成功/失敗/不確定）中，失敗路徑的具體內容就是 UX fallback。Backend 的 [fallback](/backend/knowledge-cards/fallback/) 是系統在依賴失敗時用替代結果維持服務，UX fallback 是使用者在 gate 失敗時的操作替代方案。兩者可能並存 — server-side fallback 提供降級資料，UX fallback 決定如何呈現這些降級資料給使用者。

## 可觀察訊號與例子

需要 UX fallback 的訊號是 gate 失敗時使用者完全無法繼續。常見情境：biometric 設定 `biometricOnly: true` 導致 Face ID 失敗時沒有密碼 fallback、error 畫面只有重試按鈕沒有返回按鈕、網路斷線後所有功能不可用但部分功能不依賴網路。

## 設計責任

UX fallback 的設計責任是確保 gate 失敗時使用者有路可走。Fallback 的選擇取決於安全需求和使用場景 — 銀行 app 可能不提供低安全等級的 fallback，自用工具可以接受密碼 fallback 因為使用者就是 owner。安全 vs 可用性的取捨應在功能規格中顯式記錄。UX fallback 的存在應反映在[畫面狀態矩陣](/ux-design/knowledge-cards/screen-state-matrix/)的退出路徑欄中。
