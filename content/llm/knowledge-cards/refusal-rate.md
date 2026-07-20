---
title: "Refusal Rate"
date: 2026-05-12
description: "LLM 拒絕回答 prompt 的比例、是 production LLM 服務偵測對齊強度跟異常行為的常用訊號"
weight: 1
tags: ["llm", "knowledge-cards", "safety", "monitoring"]
---

Refusal rate 的核心概念是「LLM 拒絕回答 prompt 的比例」。LLM 在訓練階段（特別是 [RLHF](/llm/knowledge-cards/rlhf/)）會學到「對特定類型的請求說『我不能幫忙這個』」、production 服務通常會監控這個比例作為對齊強度跟異常行為偵測的訊號之一。

## 概念位置

Refusal 行為的典型形態：

| 形態                     | 例子                                               |
| ------------------------ | -------------------------------------------------- |
| 安全相關拒絕             | "Sorry, I can't help with that request."           |
| 政策相關拒絕             | "I'm not able to discuss specific medical advice." |
| 能力相關拒絕             | "I don't have real-time data access."              |
| 模糊拒絕（soft refusal） | "That's an interesting question, but..."           |

Refusal rate 作為偵測訊號的兩個方向：

1. **率突然下降**：可能是對齊被繞過、[prompt injection](/llm/knowledge-cards/prompt-injection/) 攻擊在進行、或新版本模型對齊變弱。
2. **率突然上升**：可能是訓練資料或對齊政策變嚴、影響使用者體驗、或 vendor 端政策調整。

實作上、偵測 refusal 通常用簡單 pattern matching（看是否含 "I can't" / "I'm not able" / "Sorry" 等）或更精確的 classifier；具體實作依 [偵測平台](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) 設計。

> **事實查核註**：refusal rate 的標準化測量方式、跟「對齊強度」的對應關係仍在研究演進、不同 vendor 跟 model 的 baseline 差異大、引用前以對應模型的 model card 跟最新研究為準。

## 設計責任

理解 refusal rate 後可以解釋兩個現象：為什麼 production LLM 服務監控 refusal rate（變化是異常訊號）、為什麼開源模型的 refusal rate 通常低於商業旗艦（前者 safety RLHF 投入較少）。

production 設計時、refusal rate 是 content 層偵測訊號之一、需配合 tool call 序列、token usage、prompt pattern 等其他訊號才能形成完整偵測覆蓋。詳見 [LLM Service 偵測訊號覆蓋](/backend/07-security-data-protection/llm-as-service-detection-coverage/)。
