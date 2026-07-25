---
title: "DSL（Domain-Specific Language）"
date: 2026-05-14
description: "為特定業務或技術領域設計的小語言，在 LLM 應用中常作為可解析、可驗證、可執行的中介輸出"
weight: 1
tags: ["llm", "knowledge-cards", "structured-output", "dsl"]
---

DSL（Domain-Specific Language）的核心概念是「**為特定領域設計的小語言**」。它不像通用程式語言要解所有問題，而是把某個領域的可用操作、資料形狀與限制收斂成小而可解析的 [grammar](/llm/knowledge-cards/grammar/)，讓人類、LLM 與程式都能用同一種中介表示溝通。

## 概念位置

在 LLM 應用裡，DSL 常出現在自然語言與程式執行之間。模型把使用者意圖轉成 DSL，應用再 parse、validate、authorize、execute；這跟 [function calling](/llm/knowledge-cards/function-calling/) 同樣是把模型意圖收斂成可執行形式，但 DSL 比直接讓模型輸出任意程式碼更容易控管，也比純自然語言更容易自動化。

```text
使用者：「找出高優先、尚未處理的 billing ticket」
  ↓
LLM 輸出 DSL：ticket.where(category="billing", priority="high", status!="done")
  ↓
parser / validator / executor
```

## 可觀察訊號與例子

看到「特定 query language」「workflow mini-language」「policy expression」「filter expression」「tool command language」就是 DSL 候選。例子包括搜尋篩選語法、監控告警規則、資料轉換 pipeline、客服工單查詢、CI workflow 條件式。

DSL 的風險是語法看起來可控，但語意與權限仍然危險。模型生成的 DSL 要經過 parser 確認語法、validator 確認欄位與型別、authorization 確認可操作範圍、dry run 或 preview 確認副作用；不能因為輸出不是通用程式碼就直接執行。

## 設計責任

DSL 適合操作集合固定、需要高可控性、且自然語言到執行之間需要審計紀錄的場景。設計時先定義最小語法、失敗路由與不可表示狀態；需要讓 LLM 穩定產生 DSL 時，用 [grammar](/llm/knowledge-cards/grammar/) 或 JSON Schema 約束輸出。下一步路由是 [Structured Output](/llm/knowledge-cards/structured-output/) 與 [Sampling Constraint](/llm/knowledge-cards/sampling-constraint/)。
