---
title: "DSL（Domain-Specific Language）"
date: 2026-05-14
description: "為特定業務或技術領域設計的小語言，在 LLM 應用中常作為可解析、可驗證、可執行的中介輸出"
weight: 1
tags: ["llm", "knowledge-cards", "structured-output", "dsl"]
---

DSL（Domain-Specific Language）的核心概念是「**為特定領域設計的小語言**」。它不像通用程式語言要解所有問題，而是把某個領域的可用操作、資料形狀與限制收斂成小而可解析的 [grammar](/llm/knowledge-cards/grammar/)，讓人類、LLM 與程式都能用同一種中介表示溝通。

## 跟其他概念的關係

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

## 判斷條件與後果

DSL 適合三個條件同時成立的場景：操作集合固定、需要高可控性、自然語言到執行之間需要審計紀錄。操作集合不固定時，語法要跟著不斷擴充，可解析、可檢查的範圍也一起變大，DSL 相對於通用程式碼的可控優勢隨之縮小。設計時沒有先定下的三件事各有後果：語法不是最小集合時，模型能生成的合法輸入變多，validator 與 authorization 要檢查的範圍跟著變大；沒有失敗路由時，parse 或 validate 失敗的輸出沒有預先定好的去處；沒有界定不可表示的狀態時，危險的操作可能寫成合法的語法。需要讓 LLM 穩定產生合法的 DSL 時，用 [grammar](/llm/knowledge-cards/grammar/) 或 JSON Schema 約束輸出，語法不合法的字串在生成階段就被排除。下一步路由是 [Structured Output](/llm/knowledge-cards/structured-output/) 與 [Sampling Constraint](/llm/knowledge-cards/sampling-constraint/)。
