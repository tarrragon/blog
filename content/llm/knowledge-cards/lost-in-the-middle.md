---
title: "Lost in the Middle"
date: 2026-05-12
description: "LLM 對 long context 中段內容的 attention / recall 顯著低於開頭與結尾的現象"
weight: 1
tags: ["llm", "knowledge-cards", "long-context", "evaluation"]
---

Lost in the middle（中段遺失、Liu et al., 2023）的核心概念是「**LLM 對 long context 中段內容的 attention / recall 顯著低於開頭與結尾**」。實測：把答案放在 10K context 的開頭或結尾、模型 recall 準確率 80%+；放在中段 4000-6000 token 位置、recall 掉到 50% 甚至更低。是 long context 使用上最常見的失敗模式。

## 概念位置

Long context 的 effective context 跟 claimed context 落差來自三個現象：

| 現象                | 描述                                                 | 嚴重度             |
| ------------------- | ---------------------------------------------------- | ------------------ |
| Lost in the middle  | 中段內容 attention 顯著低、recall 掉                 | 普遍、最頻繁       |
| Context degradation | 接近 context 上限時、整體品質緩降                    | 接近上限才明顯     |
| Needle in haystack  | 抓單一事實的能力（vs lost-in-the-middle 抓整段邏輯） | 兩條軸、不完全重疊 |

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

## 設計責任

讀 long-context paper / benchmark 看到「lost-in-the-middle」「U-shape recall」就是這現象。寫 code 場景的判讀：

1. **把關鍵資訊放開頭或結尾**：system prompt 在開頭、最新指示在結尾（剛好是模型 attention 最強的兩處）
2. **長 context 不是「塞越多越好」**：超過 effective context（典型 8-16K）後、邊際效用急降
3. **RAG 比 long context 仍有價值**：把相關片段 retrieve 出來放 prompt 開頭、比把整份文件塞進 100K context 效果更穩定
4. **驗證自己模型的 effective context**：用 needle-in-haystack 或自製測試、看模型在 8K / 16K / 32K 表現掉到哪
5. **Reasoning model 的 thinking trace 不踩這坑嗎？** — 仍會踩、但 reasoning 過程會主動重新引用前文、部分緩解；不過 thinking trace 本身會擠壓 context budget、可能反而觸發 degradation
