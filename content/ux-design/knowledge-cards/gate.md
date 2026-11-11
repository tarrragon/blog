---
title: "Gate（UX）"
date: 2026-06-19
description: "說明使用者操作流程中「必須通過才能繼續」的關卡，以及成功/失敗/不確定三條路徑的設計責任"
weight: 2
tags: ["ux-design", "knowledge-card", "gate", "authentication"]
---

Gate 的核心概念是「使用者操作流程中必須通過才能繼續的關卡」。認證、網路連線、權限請求、環境檢查、付費牆、破壞性操作確認都是 gate。每個 gate 需要設計三條路徑：成功時做什麼、失敗時做什麼、使用者不知道發生什麼時做什麼。可先對照 [Fallback（UX）](/ux-design/knowledge-cards/ux-fallback/) 和 [Fallback（Backend）](/backend/knowledge-cards/fallback/)。

## 跟其他概念的關係

UX 語境的 gate 聚焦在使用者體驗層 — 關注的是「使用者被擋住時看到什麼、能做什麼」。和 backend 語境的 [gate decision](/backend/knowledge-cards/gate-decision/) 不同，後者關注的是部署流程中的品質關卡。Gate 的失敗路徑和不確定路徑應該反映在[畫面狀態矩陣](/ux-design/knowledge-cards/screen-state-matrix/)的退出路徑欄中。

## 可觀察訊號與例子

需要 gate 設計的訊號是使用者在某個功能前被阻擋且沒有替代路徑。常見情境：biometric 認證失敗後使用者無法進入 app、網路斷線後使用者被困在 loading 畫面、權限被拒後功能靜默消失但使用者不知道為什麼。

## 判斷條件與後果

Gate 的三條路徑缺了哪一條，使用者就在那個位置被困住。成功路徑通常最先被設計。失敗路徑沒有 [UX fallback](/ux-design/knowledge-cards/ux-fallback/)（替代驗證、降級功能、返回上一頁）時，使用者被擋在 gate 前而沒有別的路，例如 biometric 認證失敗後進不了 app；不確定路徑沒有 loading 指示和取消操作時，使用者分不出系統還在處理還是已經停住，也沒有辦法自己離開。開發環境會遮蔽 gate 的缺口：模擬器跳過認證、debug build 自動授權時，失敗與不確定路徑在開發期間從來沒有被走過；開發環境與實機的 gate 差異表，讓開發者在上機前知道哪些 gate 還沒被真實驗證。
