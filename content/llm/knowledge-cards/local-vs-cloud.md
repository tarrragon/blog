---
title: "Local vs Cloud LLM"
date: 2026-05-14
description: "用隱私、成本、延遲、能力與維運責任判斷任務該跑本地模型還是雲端模型"
weight: 1
tags: ["llm", "knowledge-cards", "architecture", "local-llm"]
---

Local vs cloud LLM 的核心概念是「**把模型執行位置視為工程取捨，而不是信仰選擇**」。本地 LLM 把資料、權重與 [推論伺服器](/llm/knowledge-cards/inference-server/) 放在自己的機器上；雲端 LLM 把 serving 與模型能力交給 provider，換取更強模型與更低維運負擔。

## 跟其他概念的關係

這個決策跨越 [three-layer architecture](/llm/knowledge-cards/three-layer-architecture/) 的所有層：介面可以相同，伺服器與模型位置不同。常見組合是同一個 IDE 介面同時接本地 [OpenAI 相容 API](/llm/knowledge-cards/openai-compatible-api/) 與雲端 API，依任務切換。

## 可觀察訊號與例子

本地適合私有資料、離線、可控成本、低資料外流風險；雲端適合高難度 reasoning、大型 agent、多模態、需要最新旗艦能力的任務。混合策略常見於 coding：本地做補完、摘要、低風險查詢，雲端處理複雜修復與大型 agent loop。

## 判斷條件與後果

本地與雲端的取捨由資料敏感度、模型能力需求、延遲體感、每月成本與維運能力共同決定，適合本地與適合雲端的任務在這幾項上的組合不同。資料不能離開自己的機器、任務又簡單（補完、摘要、低風險查詢）時，本地模型的能力已經夠用，同時省下資料外流的風險與按量計費，所以本地通常更划算，代價是硬體與伺服器的維運由自己承擔。任務需要高難度 reasoning 或大型 agent loop、失敗代價又高時，本地模型的能力不足，換成雲端旗艦提高的是成功率；雲端模型同樣會出錯，所以這類任務的人工審查不因為換到雲端而省掉。完整框架見 [0.6 本地 vs 雲端](/llm/00-foundations/local-vs-cloud/)。
