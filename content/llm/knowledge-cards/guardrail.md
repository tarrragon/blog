---
title: "Guardrail"
date: 2026-05-14
description: "在 LLM fuzzy 行為外層加上 schema、validator、policy、human review 與 monitoring 的控制設計"
weight: 1
tags: ["llm", "knowledge-cards", "safety", "architecture"]
---

Guardrail 的核心概念是「**在 LLM 的 fuzzy 行為外層加上可驗證的控制邊界**」。LLM 本身會生成機率性輸出，guardrail 用 deterministic 檢查、policy、[structured output](/llm/knowledge-cards/structured-output/)、權限與人工審查，把錯誤後果限制在可承擔範圍內。

## 跟其他概念的關係

Guardrail 是一組控制層。常見形式包含 [structured output](/llm/knowledge-cards/structured-output/)、validator、allowlist、rate limit、sandbox、human approval、eval、monitoring 與 rollback。它通常包在模型輸出與下游副作用之間。

## 可觀察訊號與例子

客服分類可以用 enum schema 限制類別；tool use 可以用 allowlist 限制可呼叫工具；production 操作可以要求 [human-in-the-loop](/llm/knowledge-cards/human-in-the-loop/) approval；外部內容進 context 前可以標記為 untrusted，降低 prompt injection 後果。

## 判斷條件與後果

Guardrail 的控制強度由失敗代價決定。輸出錯了只影響一次回答、可以重新生成的任務（客服分類），schema 擋下不合法的輸出、retry 重新生成，錯誤的後果停在一次多出來的呼叫；輸出會觸發下游副作用的任務（寫入資料、對外發送、執行指令），錯一次就留下 retry 收不回的結果，而 schema 只檢查格式、不檢查這個動作是否該做，所以這類任務在 schema 之外加 permission boundary、sandbox、審查與 audit log。相關基礎見 [Deterministic vs Fuzzy engineering](/llm/knowledge-cards/deterministic-vs-fuzzy/)。
