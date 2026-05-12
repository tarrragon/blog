---
title: "RLHF"
date: 2026-05-12
description: "Reinforcement Learning from Human Feedback：用人類偏好訓練的 reward model 透過 RL 對齊 LLM"
weight: 1
tags: ["llm", "knowledge-cards", "training", "alignment"]
---

RLHF（Reinforcement Learning from Human Feedback、人類反饋強化學習）的核心概念是「**讓人類比較兩個模型回答的好壞、訓一個 reward model 學會這個偏好、再用 RL 把 LLM 推往 reward model 給高分的方向**」。RLHF 是 LLM 對話品質飛躍的關鍵（從 GPT-3 base 到 ChatGPT 的差別主要是 RLHF）。

## 概念位置

RLHF 在訓練流程的位置與步驟：

```text
[SFT 後的模型]
   ↓
Step 1：收集人類偏好
  對同個 prompt 讓模型生 A、B 兩個 response、人類標「我較喜歡 A」
   ↓
Step 2：訓 reward model
  輸入 (prompt, response)、輸出一個分數
  目標：人類偏好的 response 分數高
   ↓
Step 3：用 PPO 等 RL 演算法 fine-tune LLM
  讓模型輸出讓 reward model 給高分的 response
  加 [KL constraint](/llm/knowledge-cards/kl-divergence/)：不能偏離 SFT model 太遠
   ↓
[Aligned model]：回答更貼近人類偏好
```

關鍵特性與挑戰：

1. **三個模型同時運作**：policy（LLM）、reward model、reference model（SFT 後 frozen 那份）、訓練時記憶體吃緊。
2. **Reward hacking**：模型可能找到 reward model 的弱點、生成「reward 高但實質爛」的輸出（如冗長 boilerplate）。
3. **訓練不穩**：PPO 對 hyperparameter 敏感、需要小心調 β（KL 約束強度）、learning rate 等。

## 設計責任

RLHF 是 ChatGPT / Claude / Gemini 等商業 LLM 對話品質的核心。讀 model card 看到「RLHF-tuned」「helpfulness fine-tuning」就是這個階段。[DPO](/llm/knowledge-cards/dpo/) 是 2023 年後出現的簡化替代方案、跳過 reward model、直接用偏好資料 fine-tune、訓練流程簡單很多、是現代許多開源模型的主流選擇。
