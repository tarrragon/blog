---
title: "Context Drift"
date: 2026-05-14
description: "Agent 長任務中累積上下文逐步偏離原始目標，導致後續行動看似合理但整體跑偏"
weight: 1
tags: ["llm", "knowledge-cards", "agent", "failure-mode"]
---

Context drift（上下文漂移）的核心概念是「**[agent loop](/llm/knowledge-cards/agent-loop/) 長任務中累積 context 逐步偏離原始目標**」。每一步局部看起來合理，但中間結果、工具輸出與模型自我敘述會逐漸取代原始任務，讓整體方向跑偏。

## 概念位置

Context drift 是 [agent loop](/llm/knowledge-cards/agent-loop/) 的長程失敗模式，跟 [goal drift](/llm/knowledge-cards/goal-drift/) 不同：goal drift 是把子目標當終點，context drift 是上下文重心逐步偏移。

## 可觀察訊號與例子

任務原本是修 bug，十步後變成重構模組，再十步後變成重寫整個檔案，就是 context drift。常見訊號是 agent 開始引用近期工具輸出當主目標，卻不再回看最初 acceptance criteria。

## 設計責任

緩解方式是定期重錨原始目標、保留 checklist、設 checkpoint、讓外部 evaluator 比對目前行動與原始任務距離。漂移持續發生時，縮短 loop、改用 single-call pipeline，或提高 human review 頻率。
