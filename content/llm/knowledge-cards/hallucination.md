---
title: "Hallucination"
date: 2026-05-12
description: "LLM 生成內容看起來合理但事實錯誤、引用不存在的來源、虛構不存在的 entity 的現象"
weight: 1
tags: ["llm", "knowledge-cards", "model-behavior", "safety"]
---

Hallucination 的核心概念是「LLM 生成的內容語法、語氣、結構看起來合理、但內容上是事實錯誤、引用不存在的來源、虛構不存在的 entity」。這是 LLM 基於統計分布生成的固有特性；以目前的研究跟工程實踐、靠「更大模型」或「更好對齊」很難徹底消除、可控的做法是用工程手段降低觸發率跟下游偵測。

## 概念位置

Hallucination 的常見形態：

| 形態            | 例子                              | 風險                         |
| --------------- | --------------------------------- | ---------------------------- |
| 虛構引用        | 引用不存在的論文 / API / 函式名稱 | 使用者照抄、出錯             |
| 虛構 entity     | 虛構不存在的公司 / 人名 / 地址    | 寫入文件、產生誤導           |
| 數值幻覺        | 給看似精確但實際錯誤的數字        | 商業 / 工程決策被誤導        |
| 因果幻覺        | 編造看似合理但不存在的因果關係    | 推理鏈不可信                 |
| 法律 / 醫療幻覺 | 虛構不存在的法條 / 治療方案       | 高風險領域、可能造成實際傷害 |

降低 / 偵測 hallucination 的常見手段（依場景變化）：

1. **[RAG](/llm/knowledge-cards/rag/)**：把真實內容檢索後注入 prompt、模型基於真實內容生成。
2. **temperature 降低**：採樣較保守、減少創造性但也減少幻覺。
3. **citation 要求**：prompt 要求列出引用、後續可驗證。
4. **下游驗證**：對輸出做事實檢查（如 code 跑 compiler、引用查實際資料庫）。
5. **明確的「不知道就說不知道」instruction**：降低過度自信、但不能消除。

> **事實查核註**：Hallucination 的研究跟降低技術仍在快速演進、不同模型、不同任務類型的 hallucination rate 變化大、引用前以最新研究跟具體 model card 為準。Stanford [TruthfulQA](https://arxiv.org/abs/2109.07958) 等 benchmark 是常見參考。

## 設計責任

理解 hallucination 後可以解釋兩個現象：為什麼 LLM 給的「具體事實」（人名 / 數字 / 引用）特別要驗證（生成機制本身就會虛構）、為什麼 LLM 寫的 code 看似合理但 import 不存在的 package（hallucinate 出 library API）。

production 場景下、hallucination 影響合規（生成包含真人 PII 的虛構內容仍是 PII 處理）、UX（使用者照抄誤導內容）、安全（生成假 URL 引發釣魚）；應對策略不是「擋住 hallucination」、是「降低觸發率 + 下游驗證 + 適當的 disclaimer」。詳見 [LLM Log 與 PII 治理](/backend/07-security-data-protection/llm-log-and-pii-governance/)。
