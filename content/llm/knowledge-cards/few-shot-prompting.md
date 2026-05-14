---
title: "Few-shot prompting"
date: 2026-05-14
description: "在 prompt 內塞 input-output 範例對齊任務、不動模型權重的 in-context learning 技術"
weight: 1
tags: ["llm", "knowledge-cards", "prompting", "in-context-learning"]
---

Few-shot prompting 的核心概念是「**在 prompt 內塞幾個 input-output 範例、讓模型透過範例對齊任務**」。Zero-shot 是不給範例直接給任務、few-shot 是給 1-N 個範例、模型從範例推任務分佈。屬於 in-context learning 的最常見形態、是「對齊任務」這件事的 prompt 層解法、跟 fine-tune 是兩個 endpoint。

## 概念位置

Zero-shot vs few-shot 對照：

```text
Zero-shot：
  Classify the tone as positive/negative/neutral.
  Review: "Fine, but I expected more."
  → 模型自己判斷「中性」邊界

Few-shot：
  Classify the tone as positive/negative/neutral.
  Examples:
    "Exceeded my expectations" → positive
    "OK, but I wish more features" → negative
    "Service was adequate" → neutral
  Review: "Fine, but I expected more."
  → 模型按範例對齊、更傾向 negative
```

Few-shot 跟 fine-tune 對照：

| 維度      | Few-shot in prompt              | Fine-tune                            |
| --------- | ------------------------------- | ------------------------------------ |
| Iteration | 分鐘級、改 prompt 即可          | 天級、要 retrain                     |
| 範例容量  | 受 context window 限制（10–50） | 可以幾千幾萬、整個 dataset 都行      |
| Cost      | 每次 inference 多付 token       | 一次性訓練 cost、之後 inference 不變 |
| 模型遷移  | 跨模型即時換、prompt 直接搬     | 綁特定 base model、換模型要 retrain  |

## 設計責任

讀 prompt engineering 文章或寫 production prompt 看到「few-shot」「in-context examples」就是這個機制。實作判讀：

1. **適用任務有「我的標準跟模型預設不同」**：分類邊界、抽取格式、tone alignment、structured output 形狀。
2. **失效在範例選不好**：cherry-picked 不代表 distribution、cover 不到 edge case、範例彼此衝突。
3. **跟 [chain-of-thought](/llm/knowledge-cards/chain-of-thought/) 可疊**（few-shot CoT 是經典組合）、跟 fine-tune 是 endpoint 取捨。
4. **何時轉 fine-tune**：範例多到撐爆 [context window](/llm/knowledge-cards/context-window/) 又每天都用、才考慮。預設先 few-shot iterate。
5. **Retrieval-augmented prompting**：把寫死的 few-shot 換成從範例庫即時 retrieve、屬於 [RAG](/llm/knowledge-cards/rag/) 概念延伸。

完整 prompt 技術 landscape 見 [4.0 Prompt 技術光譜](/llm/04-applications/prompt-techniques-landscape/)。
