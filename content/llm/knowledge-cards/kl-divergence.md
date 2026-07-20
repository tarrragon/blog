---
title: "KL Divergence"
date: 2026-05-12
description: "衡量「兩個機率分佈差距」的非對稱指標、RLHF / DPO 等 alignment 訓練的關鍵約束"
weight: 1
tags: ["llm", "knowledge-cards", "training", "math"]
---

KL divergence（Kullback-Leibler divergence、KL 散度）的核心概念是「衡量兩個機率分佈 P 跟 Q 的差距」：`KL(P ‖ Q) = sum(P(x) × log(P(x) / Q(x)))`。它**不對稱**（`KL(P ‖ Q) ≠ KL(Q ‖ P)`）、所以不算「距離」、是「散度」。在 LLM 訓練中是 [RLHF](/llm/knowledge-cards/rlhf/) / [DPO](/llm/knowledge-cards/dpo/) 等 alignment 階段防止模型「為了 reward 偏離太遠」的關鍵約束。

## 概念位置

KL divergence 在 LLM 中的兩個主要角色：

1. **跟 [cross-entropy](/llm/knowledge-cards/cross-entropy/) 的關係**：

   ```text
   cross-entropy(P, Q) = entropy(P) + KL(P ‖ Q)
   ```

   訓練時 P（真實分佈）固定、entropy(P) 是常數、所以「minimize cross-entropy」等於「minimize KL」。

2. **RLHF / DPO 的「KL 約束」**：

   alignment 階段不能只 maximize reward、否則模型會「為了 reward 把語言能力毀掉」。所以加 KL 約束：

   ```text
   objective = E[reward] - β × KL(π_new ‖ π_ref)
                            └─ 不讓新模型偏離 ref（通常是 SFT 後的 base）太遠 ─┘
   ```

   β 控制「reward 追求」vs「不偏離原始模型」的平衡。

跟相關概念的對比：

| 指標          | 對稱？ | 主要用途                              |
| ------------- | ------ | ------------------------------------- |
| Cross-entropy | 否     | 訓練 loss、衡量預測機率分佈跟真實分佈 |
| KL divergence | 否     | Alignment 訓練的偏離約束              |
| JS divergence | 是     | 兩個分佈的對稱差距、研究比較多        |

## 設計責任

讀 alignment paper 看到 β、KL penalty、KL coefficient 等詞、知道這些是控制「模型在追 reward 時偏離 base 多遠的容忍度」。β 太小、模型容易 reward hacking（找 reward 高但實質爛的輸出）；β 太大、模型動不了、reward 升不上去。DPO 把 KL 約束內嵌進 loss、不像 RLHF 需要顯式 KL term、是 DPO 比 RLHF 簡單的原因之一。
