---
title: "Lost in the Middle"
date: 2026-05-12
description: "LLM 對 long context 中段內容的 attention / recall 顯著低於開頭與結尾的現象"
weight: 1
tags: ["llm", "knowledge-cards", "long-context", "evaluation"]
---

Lost in the middle（中段遺失、Liu et al., 2023）的核心概念是「**LLM 對 long context 中段內容的 attention / recall 顯著低於開頭與結尾**」。實測：把答案放在 10K context 的開頭或結尾、模型 recall 準確率 80%+；放在中段 4000-6000 token 位置、recall 掉到 50% 甚至更低。是 [long context](/llm/knowledge-cards/context-window/) 使用上最常見的失敗模式。

## 跟其他概念的關係

Long context 的 effective context 跟 claimed context 落差來自三個現象：

| 現象                                                           | 描述                                                 | 嚴重度             |
| -------------------------------------------------------------- | ---------------------------------------------------- | ------------------ |
| Lost in the middle                                             | 中段內容 attention 顯著低、recall 掉                 | 普遍、最頻繁       |
| Context degradation                                            | 接近 context 上限時、整體品質緩降                    | 接近上限才明顯     |
| [Needle in haystack](/llm/knowledge-cards/needle-in-haystack/) | 抓單一事實的能力（vs lost-in-the-middle 抓整段邏輯） | 兩條軸、不完全重疊 |

```text
Recall accuracy vs 答案位置（典型 10K context）：

100% |█                                       █
     |██                                     ██
 80% |███                                   ███
     |███                                   ███
 60% |███          ____                     ███
     |███      ___/    \___                 ███
 40% |███    _/            \_               ███
     |█████─/                \─────         ███
     |
       0      2K     4K     6K     8K    10K
       開頭                              結尾
```

成因：

1. **Attention weight 分佈不均勻**：訓練資料中、句首 / 段首通常含關鍵資訊、模型學會偏重句首；長 context 的中段在訓練資料中相對稀疏、attention 沒學好
2. **Positional encoding 設計**：RoPE / ALiBi 等對長距離 attention 的衰減模式、中段 token 跟 query 距離通常較大、attention 弱
3. **訓練 context 長度的影響**：模型若訓練在 8K context、推論時用 128K（用 RoPE scaling 延伸）、中段表現比訓練範圍內差更多

## 判斷條件與後果

關鍵資訊在 context 裡的位置，決定模型是否抓得到它：開頭與結尾的 recall 最高，中段最低（〈跟其他概念的關係〉裡的 recall 曲線）。system prompt 在開頭、最新指示在結尾時，兩者剛好落在 attention 最強的兩處；關鍵段落夾在一長串文件中間時，模型照樣讀進去了，回答卻可能漏掉它。

context 長度超過模型的 effective context（典型 8-16K）之後，多塞進去的內容落進中段，邊際效用急降。所以把整份文件塞進 100K context，常常不如用 [RAG](/llm/knowledge-cards/rag/) 把相關片段 retrieve 出來放在 prompt 開頭穩定。effective context 每個模型不同，宣稱的 context 長度代表不了它，用 [needle-in-haystack](/llm/knowledge-cards/needle-in-haystack/) 或自製測試在 8K、16K、32K 各量一次，才看得到表現從哪個長度開始掉。

reasoning model 同樣有中段遺失：reasoning 過程會主動重新引用前文，部分緩解這個現象；thinking trace 本身也佔 context budget，長任務裡它把 context 推近上限時，反而可能觸發 context degradation。
