---
title: "RLHF"
date: 2026-05-12
description: "Reinforcement Learning from Human Feedback：用人類偏好訓練的 reward model 透過 RL 對齊 LLM"
weight: 1
tags: ["llm", "knowledge-cards", "training", "alignment"]
---

RLHF（Reinforcement Learning from Human Feedback、人類反饋強化學習）的核心概念是「**在 [SFT](/llm/knowledge-cards/sft/) 之後、讓人類比較兩個模型回答的好壞、訓一個 reward model 學會這個偏好、再用 RL 把 LLM 推往 reward model 給高分的方向**」。RLHF 是 LLM 對話品質飛躍的關鍵（從 GPT-3 base 到 ChatGPT 的差別主要是 RLHF）。

## 跟其他概念的關係

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
3. **訓練不穩**：PPO 對 hyperparameter 敏感、需要小心調 β（KL 約束強度）、[learning rate](/llm/knowledge-cards/learning-rate/) 等。

## 判斷條件與後果

RLHF 是 ChatGPT / Claude / Gemini 等商業 LLM 對話品質的核心。讀 model card 看到「RLHF-tuned」「helpfulness fine-tuning」就是這個階段。[DPO](/llm/knowledge-cards/dpo/) 是 2023 年後出現的簡化替代方案、跳過 reward model、直接用偏好資料 fine-tune、訓練流程簡單很多、是現代許多開源模型的主流選擇。

自己做偏好對齊時，在 RLHF 與 DPO 之間選，看的是訓練資源，以及是否接受訓練不穩帶來的重跑成本。RLHF 訓練時 policy、reward model、reference model 三個模型同時在記憶體裡，硬體放不下三份時無法用 RLHF 訓練；放得下時，PPO 對 β 與 learning rate 敏感，每一組設定都可能要重跑才找得到收斂的那一組，算力成本按重跑次數加倍。DPO 不訓 reward model，訓練時少一個模型，也沒有 PPO 的調參，所以資源有限時多半選 DPO。訓練出來的模型回答愈來愈長、塞滿套話而 reward 分數仍在上升時，代表 policy 找到了 reward model 給高分卻不符合人類偏好的寫法（reward hacking），原因是 policy 優化的對象是 reward model 的分數，而 reward model 只是人類偏好的近似；這時調高 β，讓 KL constraint 把 policy 的輸出限制在 SFT model 附近。
