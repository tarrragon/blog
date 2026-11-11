---
title: "LLM Agent"
date: 2026-05-11
description: "把控制流交給 LLM 的應用模式：自主決策、跨多步呼叫工具、人類角色從主導變監督"
weight: 1
tags: ["llm", "knowledge-cards"]
---

LLM Agent 的核心概念是「把控制流的所有權從人類交給 LLM」。傳統對話 LLM 是「人類問、模型答」、每輪 turn 獨立；agent 是「LLM 自己決定下一步、自己呼叫[工具](/llm/knowledge-cards/tool-use/)、自己評估結果」、跨多步累積 context。

## 跟其他概念的關係

Agent 是應用層的工作流模式、建立在 [tool use](/llm/knowledge-cards/tool-use/)、[function calling](/llm/knowledge-cards/function-calling/)、[structured output](/llm/knowledge-cards/structured-output/)、[autoregressive](/llm/knowledge-cards/autoregressive/) 生成之上。Agent loop 五步骨架（感知 → 推理 → 行動 → 觀察 → 判斷終止）是所有 agent framework 的共通結構、不論具體實作。本地 LLM 受 tool use 訓練不足、長 context prefill 痛點（見 [TTFT](/llm/knowledge-cards/ttft/)、[prefill](/llm/knowledge-cards/prefill/)）、規劃能力弱等限制、跑 agent 現階段失敗率高於雲端旗艦。

## 可觀察訊號與例子

寫 code 場景的代表 agent：aider、Cline、Cursor Agent。判讀 agent 失敗訊號分三類：**context drift**（累積偏離原目標）、**目標漂移**（子目標完成就停、原任務沒完成）、**tool 結果誤判**（tool 回 error 模型 hallucinate「成功」繼續推）。

## 判斷條件與後果

任務是否適合交給 agent，看兩個條件是否同時成立：任務拆得出明確的子步驟，而且每一步都有客觀的驗證訊號（test 通過、file 寫入成功）。兩者都成立時，agent 每一步都能用驗證訊號決定往下走或重做；模糊的探索性任務缺驗證訊號，agent 只能靠自己判斷做完了沒有，上面列的目標漂移與 tool 結果誤判都出在這個位置，所以這類任務用 single-call 加上人的判讀，出錯的機會較少。Agent 跑有副作用的任務時，人類審查的粒度跟著副作用的可逆性定：可逆的操作出錯可以回滾，全自動的代價只是重做；不可逆的操作出錯無法回滾，所以改成每一步都由人核准（step-by-step approval）。詳細展開見 [4.4 Agent 架構原理](/llm/04-applications/agent-architecture/)。
