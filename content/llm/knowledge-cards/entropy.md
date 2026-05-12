---
title: "Entropy"
date: 2026-05-12
description: "資訊論衡量「分佈的不確定性」的指標、cross-entropy / KL divergence 的基底"
weight: 1
tags: ["llm", "knowledge-cards", "math", "information-theory"]
---

Entropy（熵）的核心概念是「衡量一個機率分佈的不確定性」。Shannon entropy 公式：`H(P) = -sum(P(x) × log P(x))`。直覺：分佈越「平」、entropy 越大（任何結果都可能）；分佈越「尖」、entropy 越小（結果很確定）。Entropy 是 [cross-entropy](/llm/knowledge-cards/cross-entropy/)、[KL divergence](/llm/knowledge-cards/kl-divergence/)、資訊壓縮等概念的基底。

## 概念位置

Entropy 跟 LLM 相關概念的關係：

```text
Entropy(P) = -sum P log P                  ← 一個分佈自身的不確定性
Cross-entropy(P, Q) = -sum P log Q         ← 用分佈 Q 編碼 P 的成本
KL(P ‖ Q) = Cross-entropy(P, Q) - Entropy(P) ← 兩個分佈的差距
```

Entropy 在 LLM 中的具體意義：

| 場景                     | Entropy 大                                | Entropy 小               |
| ------------------------ | ----------------------------------------- | ------------------------ |
| 模型 next-token 預測分佈 | 「不確定下個字、可能 N 種選項」           | 「強烈傾向某幾個 token」 |
| Sampling temperature 高  | Entropy 高、輸出多樣                      | Entropy 低、輸出確定     |
| 訓練未收斂               | 分佈接近 uniform、entropy 接近 log(vocab) | 分佈集中、entropy 降低   |

範例：vocab = 128K、uniform 分佈的 entropy = log(128K) ≈ 11.76（接近 12）；成熟模型在文本上的平均 entropy 約 2-3。

## 設計責任

Entropy 本身在 LLM 訓練 / 推論很少直接出現、但理解它能解釋一些現象：[perplexity](/llm/knowledge-cards/perplexity/) = exp(cross-entropy) 是模型平均不確定性的指數形式；temperature 控制 sampling entropy（高 T → 高 entropy → 多樣輸出）；某些評估方法（如 entropy-based uncertainty estimation）會看模型輸出分佈的 entropy 來判讀「模型有多確定」。
