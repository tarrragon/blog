---
title: "LLM Agent"
date: 2026-05-11
description: "把控制流交給 LLM 的應用模式：自主決策、跨多步呼叫工具、人類角色從主導變監督"
weight: 1
tags: ["llm", "knowledge-cards"]
---

LLM Agent 的核心概念是「把控制流的所有權從人類交給 LLM」。傳統對話 LLM 是「人類問、模型答」、每輪 turn 獨立；agent 是「LLM 自己決定下一步、自己呼叫[工具](/llm/knowledge-cards/tool-use/)、自己評估結果」、跨多步累積 context。

## 概念位置

Agent 是應用層的工作流模式、建立在 [tool use](/llm/knowledge-cards/tool-use/)、[function calling](/llm/knowledge-cards/function-calling/)、[structured output](/llm/knowledge-cards/structured-output/)、[autoregressive](/llm/knowledge-cards/autoregressive/) 生成之上。Agent loop 五步骨架（感知 → 推理 → 行動 → 觀察 → 判斷終止）是所有 agent framework 的共通結構、不論具體實作。本地 LLM 受 tool use 訓練不足、長 context prefill 痛點（見 [TTFT](/llm/knowledge-cards/ttft/)、[prefill](/llm/knowledge-cards/prefill/)）、規劃能力弱等限制、跑 agent 現階段失敗率高於雲端旗艦。

## 可觀察訊號與例子

寫 code 場景的代表 agent：aider、Cline、Cursor Agent。判讀 agent 失敗訊號分三類：**context drift**（累積偏離原目標）、**目標漂移**（子目標完成就停、原任務沒完成）、**tool 結果誤判**（tool 回 error 模型 hallucinate「成功」繼續推）。

## 設計責任

決定該用 agent 還是 single-call、看任務是否有明確子步驟 + 客觀驗證訊號（test 通過、file 寫入）。模糊探索性任務不適合 agent。Agent 跑高風險任務時、人類審查粒度應該配合工具的副作用範圍——可逆任務全自動、不可逆任務 step-by-step approval。詳細展開見 [4.4 Agent 架構原理](/llm/04-applications/agent-architecture/)。
