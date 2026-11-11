---
title: "Function Calling"
date: 2026-05-11
description: "模型訓練階段建立的「呼叫工具」能力：知道何時該呼叫、傳什麼參數"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Function Calling 的核心概念是「模型在訓練階段學到的呼叫工具能力」。[SFT](/llm/knowledge-cards/sft/) 階段大量「使用者 query + 該呼叫什麼工具 + 傳什麼參數」的範例、讓模型學會看到 query 知道何時呼叫、怎麼呼叫、傳什麼參數。

## 跟其他概念的關係

Function calling 是**模型能力**層、跟 [structured output](/llm/knowledge-cards/structured-output/)（**[sampling 約束](/llm/knowledge-cards/sampling-constraint/)**層）、[MCP](/llm/knowledge-cards/mcp/)（**server 協議**層）正交。三者解的問題層級不同、可獨立或組合使用。模型訓練支撐 vs sampling 強制的差別決定行為穩定性：function calling 訓練好的模型「自然」輸出合法呼叫、不需要強約束；訓練不足靠 structured output 兜底。

## 可觀察訊號與例子

模型 function calling 強弱看四個指標：(1) 該呼叫時呼叫的準確度、(2) 呼叫格式合法率、(3) 參數準確度、(4) 多工具選對工具的準確度。寫 code 場景的本地小模型（< 14B）這四個都明顯弱於雲端旗艦——根因是 SFT 階段 function calling 範例量不夠、小模型容量學不全。判讀訊號：呼叫格式錯、參數胡亂填、不該呼叫時呼叫、該呼叫時不呼叫。

## 判斷條件與後果

Function calling 跟 free-form 輸出加 structured output 之間的選擇，看模型的 function calling 訓練是否足夠，以及系統是否要在幾個模型之間切換。主流大模型的 SFT 階段有大量呼叫範例，模型自己輸出合法呼叫，直接用 function calling 不需要額外約束；本地小模型的呼叫格式錯、參數亂填比例高（上一段的訊號），要跨模型使用時各模型的呼叫能力也隨訓練而不同，這兩種情形改用 free-form 輸出加 [grammar](/llm/knowledge-cards/grammar/) 約束，格式的合法由 sampling 階段強制，不依賴模型的訓練。兩者也可以疊用：正常情況走 function calling，structured output 兜底保證格式合法，retry 與 fallback 處理格式合法而內容錯的呼叫（選錯工具、參數值錯），原因是 sampling 約束只管形狀，管不到選哪個工具。詳細展開見 [4.3 Tool use 原理](/llm/04-applications/tool-use-principles/) 與 [4.6 應用層協議](/llm/04-applications/application-protocols/)。
