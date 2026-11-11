---
title: "Few-shot prompting"
date: 2026-05-14
description: "在 prompt 內塞 input-output 範例對齊任務、不動模型權重的 in-context learning 技術"
weight: 1
tags: ["llm", "knowledge-cards", "prompting", "in-context-learning"]
---

Few-shot prompting 的核心概念是「**在 prompt 內塞幾個 input-output 範例、讓模型透過範例對齊任務**」。Zero-shot 是不給範例直接給任務、few-shot 是給 1-N 個範例、模型從範例推任務分佈。屬於 [in-context learning](/llm/knowledge-cards/in-context-learning/) 的最常見形態、是「對齊任務」這件事的 prompt 層解法、跟 fine-tune 是兩個 endpoint。

## 跟其他概念的關係

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

Few-shot 跟 [fine-tune](/llm/knowledge-cards/sft/) 對照：

| 維度      | Few-shot in prompt              | Fine-tune                            |
| --------- | ------------------------------- | ------------------------------------ |
| Iteration | 分鐘級、改 prompt 即可          | 天級、要 retrain                     |
| 範例容量  | 受 context window 限制（10–50） | 可以幾千幾萬、整個 dataset 都行      |
| Cost      | 每次 inference 多付 token       | 一次性訓練 cost、之後 inference 不變 |
| 模型遷移  | 跨模型即時換、prompt 直接搬     | 綁特定 base model、換模型要 retrain  |

## 判斷條件與後果

Few-shot 的效果取決於任務的標準跟模型預設的差距。分類邊界、抽取格式、語氣、structured output 的形狀這類由使用者定義的標準，zero-shot 時模型照自己的預設判斷（上面的例子裡 "Fine, but I expected more." 的中性邊界由模型自己決定），給了範例之後模型照範例對齊，原因是模型只能從 prompt 的文字得知使用者的標準，範例把這個標準具體寫了出來。

- **範例不代表實際輸入的分佈時**（只挑了好看的範例、沒涵蓋 edge case、範例彼此衝突），模型對齊的是範例的偏差，edge case 的輸出照樣不穩，原因是模型只能從給的範例推任務分佈。
- **任務同時需要推理步驟時**，few-shot 可以跟 [chain-of-thought](/llm/knowledge-cards/chain-of-thought/) 疊用（few-shot CoT）：範例對齊輸出的標準，推理步驟讓模型寫出中間結果，兩者作用在不同的位置。
- **範例多到佔滿 [context window](/llm/knowledge-cards/context-window/)、而且每天重複使用時**，每次 inference 都重付同一批範例的 token，分鐘級迭代的好處被 context 上限與 token 成本抵掉，fine-tune 的一次性訓練成本這時才划算（上面的對照表）；範例量還在 context 容量內時，改 prompt 的迭代比 retrain 快得多，所以 few-shot 是先試的那一端。
- **合適的範例隨輸入而變時**，寫死的範例改成從範例庫即時 retrieve 最相近的幾個，這是 [RAG](/llm/knowledge-cards/rag/) 的做法用在範例上：檢索的對象是範例，不是文件。

完整 prompt 技術 landscape 見 [4.0 Prompt 技術光譜](/llm/04-applications/prompt-techniques-landscape/)。
