---
title: "Gate（UX）"
date: 2026-06-19
description: "說明使用者操作流程中「必須通過才能繼續」的關卡，以及成功/失敗/不確定三條路徑的設計責任"
weight: 2
tags: ["ux-design", "knowledge-card", "gate", "authentication"]
---

Gate 的核心概念是「使用者操作流程中必須通過才能繼續的關卡」。認證、網路連線、權限請求、環境檢查、付費牆都是 gate。每個 gate 需要設計三條路徑：成功時做什麼、失敗時做什麼、使用者不知道發生什麼時做什麼。可先對照 [Fallback（UX）](/ux-design/knowledge-cards/ux-fallback/) 和 [Fallback（Backend）](/backend/knowledge-cards/fallback/)。

## 概念位置

UX 語境的 gate 聚焦在使用者體驗層 — 關注的是「使用者被擋住時看到什麼、能做什麼」。和 backend 語境的 [gate decision](/backend/knowledge-cards/gate-decision/) 不同，後者關注的是部署流程中的品質關卡。Gate 的失敗路徑和不確定路徑應該反映在[畫面狀態矩陣](/ux-design/knowledge-cards/screen-state-matrix/)的退出路徑欄中。

## 可觀察訊號與例子

需要 gate 設計的訊號是使用者在某個功能前被阻擋且沒有替代路徑。常見情境：biometric 認證失敗後使用者無法進入 app、網路斷線後使用者被困在 loading 畫面、權限被拒後功能靜默消失但使用者不知道為什麼。

## 設計責任

Gate 的設計責任是確保每條路徑都有明確的使用者體驗。成功路徑通常最先被設計；失敗路徑需要提供 [UX fallback](/ux-design/knowledge-cards/ux-fallback/)（替代驗證、降級功能、返回上一頁）；不確定路徑需要 loading 指示和取消操作。開發環境可能遮蔽 gate 問題 — 模擬器跳過認證、debug build 自動授權 — 差異表讓開發者在上機前知道哪些 gate 還沒被真實驗證。
