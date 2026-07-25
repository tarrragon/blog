---
title: "Tool Result Misread"
date: 2026-05-14
description: "Agent 誤讀工具輸出，把錯誤、空結果或部分成功當成成功，導致後續步驟建立在錯誤狀態上"
weight: 1
tags: ["llm", "knowledge-cards", "agent", "tool-use"]
---

Tool result misread（工具結果誤判）的核心概念是「**agent 把 [tool use](/llm/knowledge-cards/tool-use/) 輸出的錯誤或不完整狀態解讀成成功**」。LLM 只看文字與結構化回傳，若工具結果設計不清楚，模型容易忽略 error、warning、空集合或 partial failure。

## 概念位置

它是 [tool use](/llm/knowledge-cards/tool-use/) 與 [agent loop](/llm/knowledge-cards/agent-loop/) 交界的失敗模式。模型可能選對工具、也成功呼叫工具，但在 observe 階段錯讀結果。

## 可觀察訊號與例子

`git push` 失敗，agent 卻開始寫 PR description；查詢回空集合，agent 卻假設資料存在；測試命令非零退出，agent 只讀到最後幾行 log 就當成功。這些都是工具結果誤判。

## 設計責任

工具回傳要結構化表示 status、exit code、error type、stdout/stderr 與可重試性。Agent loop 要在 error signal 出現時強制 re-read 或 retry，必要時呼叫狀態確認工具，而不是依賴模型記憶。
