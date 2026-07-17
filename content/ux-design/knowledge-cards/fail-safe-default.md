---
title: "Fail-safe 預設（安全預設）"
date: 2026-07-17
description: "說明保護機制本身故障時系統倒向哪個方向的設計決策 — 預設倒向不可逆性低的那邊，確認 UI 壞掉不該讓破壞性操作靜默通過"
weight: 9
tags: ["ux-design", "knowledge-card", "fail-safe", "gate", "destructive-action"]
---

Fail-safe 預設的核心概念是「保護機制本身故障時，系統選擇倒向哪個方向」。確認對話框沒渲染、事件沒綁上、回應逾時 — 這些故障發生時系統仍要做一個決定：把故障當同意（執行）或當拒絕（不執行）。安全預設的原則是倒向不可逆性低的那邊：不清空可以重試、清空無法還原。這是 [Gate](/ux-design/knowledge-cards/gate/) 的第二層設計 — gate 攔使用者、fail-safe 管 gate 自己壞掉的情況。

## 概念位置

Fail-safe 預設與 [UX Fallback](/ux-design/knowledge-cards/ux-fallback/) 的分工：fallback 是給使用者的替代路徑（主路徑失敗後使用者往哪走）、fail-safe 是系統自己的預設方向（保護機制失效時系統做什麼）— 前者是使用者可見的路、後者是程式碼裡的 else 分支。安全領域的對應概念是 fail-open vs fail-closed：破壞性操作的確認機制要 fail-closed（故障即拒絕）。

## 可觀察訊號與例子

需要檢查 fail-safe 的訊號是「保護邏輯存在、但它的故障分支沒人設計過」。實戰正面案例：匯入覆蓋模式的確認 Modal 在 DOM 缺失時一律視為未確認、預設不清空書庫（[U.C12](/ux-design/cases/destructive-import-fail-safe-confirm/)）。反向的檢查問句：確認元件不存在時、你的程式碼走哪個分支？

## 設計責任

Fail-safe 的設計責任是為每個保護機制（確認對話框、權限檢查、二次驗證）顯式寫下故障分支的方向。程式碼層的掃描訊號：確認邏輯的 else / null / timeout 分支最終呼叫的是「執行」還是「中止」— 分支缺失或走向執行的，就是故障會靜默放行破壞的候選。
