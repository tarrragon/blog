---
title: "Tool Result Misread"
date: 2026-05-14
description: "Agent 誤讀工具輸出，把錯誤、空結果或部分成功當成成功，導致後續步驟建立在錯誤狀態上"
weight: 1
tags: ["llm", "knowledge-cards", "agent", "tool-use"]
---

Tool result misread（工具結果誤判）的核心概念是「**agent 把 [tool use](/llm/knowledge-cards/tool-use/) 輸出的錯誤或不完整狀態解讀成成功**」。LLM 只看文字與結構化回傳，若工具結果設計不清楚，模型容易忽略 error、warning、空集合或 partial failure。

## 跟其他概念的關係

它是 [tool use](/llm/knowledge-cards/tool-use/) 與 [agent loop](/llm/knowledge-cards/agent-loop/) 交界的失敗模式。模型可能選對工具、也成功呼叫工具，但在 observe 階段錯讀結果。

## 可觀察訊號與例子

`git push` 失敗，agent 卻開始寫 PR description；查詢回空集合，agent 卻假設資料存在；測試命令非零退出，agent 只讀到最後幾行 log 就當成功。這些都是工具結果誤判。

## 判斷條件與後果

工具回傳只有一段自由文字時，error、warning、空集合與 partial failure 混在 log 裡，模型在 observe 階段可能只讀到最後幾行就判成成功，後面的步驟建立在一個沒有發生的結果上（`git push` 失敗後照樣寫 PR description）；原因是 LLM 只讀得到工具回傳的文字，失敗的訊號被截斷或埋在中段時，模型手上沒有別的來源可以對照。回傳把 status、exit code、error type、stdout/stderr 與可重試性分成各自的欄位時，失敗是一個獨立的值，agent loop 拿得到一個可以檢查的訊號。模型記得的先前結果可能已經過時或本來就讀錯，所以 error signal 出現時，agent loop 以 re-read、retry 或呼叫狀態確認工具取得當下的狀態，不沿用模型記憶。
