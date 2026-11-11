---
title: "Goal Drift"
date: 2026-05-14
description: "Agent 把子目標誤當成整體目標，提早停止或朝錯誤完成條件前進的失敗模式"
weight: 1
tags: ["llm", "knowledge-cards", "agent", "failure-mode"]
---

Goal drift（目標漂移）的核心概念是「**[agent loop](/llm/knowledge-cards/agent-loop/) 把子目標誤當成整體目標**」。它常讓模型完成局部步驟後宣告任務完成，實際上還漏掉測試、驗證、提交、回報或其他原始要求。

## 跟其他概念的關係

Goal drift 是 [agent loop](/llm/knowledge-cards/agent-loop/) 的 termination 失敗。它跟 [context drift](/llm/knowledge-cards/context-drift/) 的差異是：context drift 是上下文逐步偏移，goal drift 是完成條件被錯誤替換。

## 可觀察訊號與例子

原任務是「實作、測試、commit」，agent 實作完就回答「已完成」，這是 goal drift。另一個訊號是 agent 每步都在完成一個合理子任務，但沒有維護整體 checklist。

## 判斷條件與後果

Goal drift 的判斷看完成條件由誰認定。完成只靠模型自評時，agent 完成一個子任務就可能宣告整體完成，漏掉的測試、提交或回報要到下游才被發現，原因是自評時模型對照的是它當下的目標，而 goal drift 替換掉的正是這個目標。完成條件外部化成可檢查的事實（test pass、檔案存在、PR 開啟、commit hash 產生、人工批准）時，宣告完成要先通過這些檢查，漂移後的子目標通過不了。漏掉一步的代價隨任務的副作用變大，所以高風險任務用 checklist 與 deterministic gate 擋住提早宣告的完成。
