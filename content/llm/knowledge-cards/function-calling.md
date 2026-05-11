---
title: "Function Calling"
date: 2026-05-11
description: "模型訓練階段建立的「呼叫工具」能力：知道何時該呼叫、傳什麼參數"
weight: 1
tags: ["llm", "knowledge-cards"]
---

Function Calling 的核心概念是「模型在訓練階段學到的呼叫工具能力」。SFT 階段大量「使用者 query + 該呼叫什麼工具 + 傳什麼參數」的範例、讓模型學會看到 query 知道何時呼叫、怎麼呼叫、傳什麼參數。

## 概念位置

Function calling 是**模型能力**層、跟 structured output（**sampling 約束**層）、[MCP](/llm/knowledge-cards/mcp/)（**server 協議**層）正交。三者解的問題層級不同、可獨立或組合使用。模型訓練支撐 vs sampling 強制的差別決定行為穩定性：function calling 訓練好的模型「自然」輸出合法呼叫、不需要強約束；訓練不足靠 structured output 兜底。

## 可觀察訊號與例子

模型 function calling 強弱看四個指標：(1) 該呼叫時呼叫的準確度、(2) 呼叫格式合法率、(3) 參數準確度、(4) 多工具選對工具的準確度。寫 code 場景的本地小模型（< 14B）這四個都明顯弱於雲端旗艦——根因是 SFT 階段 function calling 範例量不夠、小模型容量學不全。判讀訊號：呼叫格式錯、參數胡亂填、不該呼叫時呼叫、該呼叫時不呼叫。

## 設計責任

選擇 function calling 還是 free-form + structured output、依模型規模跟跨 model 可移植需求決定：主流大模型走 function calling 開箱即用、跨 model / 較弱模型走 free-form + grammar 約束較穩。實務常組合：function calling 「正常情況」、structured output 兜底保證合法、retry + fallback 處理失敗。詳細展開見 [4.1 Tool use 原理](/llm/04-applications/tool-use-principles/) 與 [4.3 應用層協議](/llm/04-applications/application-protocols/)。
