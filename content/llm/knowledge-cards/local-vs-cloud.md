---
title: "Local vs Cloud LLM"
date: 2026-05-14
description: "用隱私、成本、延遲、能力與維運責任判斷任務該跑本地模型還是雲端模型"
weight: 1
tags: ["llm", "knowledge-cards", "architecture", "local-llm"]
---

Local vs cloud LLM 的核心概念是「**把模型執行位置視為工程取捨，而不是信仰選擇**」。本地 LLM 把資料、權重與 [推論伺服器](/llm/knowledge-cards/inference-server/) 放在自己的機器上；雲端 LLM 把 serving 與模型能力交給 provider，換取更強模型與更低維運負擔。

## 概念位置

這個決策跨越 [three-layer architecture](/llm/knowledge-cards/three-layer-architecture/) 的所有層：介面可以相同，伺服器與模型位置不同。常見組合是同一個 IDE 介面同時接本地 [OpenAI 相容 API](/llm/knowledge-cards/openai-compatible-api/) 與雲端 API，依任務切換。

## 可觀察訊號與例子

本地適合私有資料、離線、可控成本、低資料外流風險；雲端適合高難度 reasoning、大型 agent、多模態、需要最新旗艦能力的任務。混合策略常見於 coding：本地做補完、摘要、低風險查詢，雲端處理複雜修復與大型 agent loop。

## 設計責任

判斷時看五個訊號：資料敏感度、模型能力需求、延遲體感、每月成本、維運能力。當任務失敗代價高且能力要求高，雲端未必可替代人工審查；當資料敏感且任務簡單，本地模型通常更划算。完整框架見 [0.6 本地 vs 雲端](/llm/00-foundations/local-vs-cloud/)。
