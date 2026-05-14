---
title: "Structured Output"
date: 2026-05-14
description: "讓 LLM 輸出可被 parser 穩定消費的推論階段設計：JSON mode、schema-guided decoding、grammar 約束都屬於這一層"
weight: 1
tags: ["llm", "knowledge-cards", "structured-output", "sampling"]
---

Structured output 的核心概念是「**讓 LLM 輸出符合可機器解析的固定形狀**」。它解的是應用層 parser 能不能穩定消費模型輸出的問題：輸出要能被 JSON parser、schema validator、dispatcher、workflow engine 確定性處理，而不是靠人類讀自然語言再猜意圖。

## 概念位置

Structured output 位在推論與應用交界，常見實作包含 JSON mode、JSON Schema、[grammar](/llm/knowledge-cards/grammar/) 約束、[constrained decoding](/llm/knowledge-cards/constrained-decoding/) 與 logit mask。它跟 [function calling](/llm/knowledge-cards/function-calling/) 的差異在責任層：function calling 是模型訓練出的工具呼叫能力，structured output 是推論時讓輸出形狀穩定的約束。

```text
模型能力：知道是否該呼叫工具、該填什麼參數
推論約束：輸出必須符合 JSON / schema / grammar
應用消費：parser 解析、validator 檢查、dispatcher 執行
```

## 可觀察訊號與例子

看到「固定輸出 JSON」「把結果分類成 enum」「回傳符合 schema 的物件」「讓 parser 不再處理自由文字」就是 structured output 場景。例子是客服工單分類：模型輸出 `{"category":"billing","priority":"high"}`，後端可以直接依欄位路由，而不是從一段自然語言裡抽關鍵字。

Structured output 的成功訊號是合法率、schema 對位率與下游解析失敗率。JSON 合法率只代表文字可被 parser 讀，schema 對位率才代表欄位、型別、enum、required 都符合應用契約；兩者分開看，才能分辨是語法錯、schema 錯，還是模型語意判斷錯。

## 設計責任

Structured output 適合「下游要自動執行」的輸出：tool 參數、分類、抽取、workflow 狀態、查詢條件。它的邊界是語意品質：grammar 可以保證格式合法，但不能保證模型填的值正確。下一步路由是：需要理解 token mask 機制讀 [Constrained Decoding](/llm/knowledge-cards/constrained-decoding/)；需要判斷它跟工具呼叫的分工讀 [Function Calling](/llm/knowledge-cards/function-calling/)；需要完整應用層組合讀 [4.6 應用層協議](/llm/04-applications/application-protocols/)。
