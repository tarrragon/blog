---
title: "Loss Function"
date: 2026-05-12
description: "把「模型預測」跟「正確答案」的差距量化成一個純量、訓練的最佳化目標"
weight: 1
tags: ["llm", "knowledge-cards", "training", "math"]
---

Loss function（損失函數、目的函數）的核心概念是「把模型預測跟正確答案的差距、壓成一個純量數值」。訓練的整個目標就是「最小化這個數值」、所有 [gradient](/llm/knowledge-cards/gradient/) / [backpropagation](/llm/knowledge-cards/backpropagation/) / optimizer step 都在做這件事。

## 概念位置

LLM 各訓練階段用不同的 loss function：

| 階段         | 主要 loss                                                                     | 衡量的東西                                |
| ------------ | ----------------------------------------------------------------------------- | ----------------------------------------- |
| Pre-training | [Cross-entropy](/llm/knowledge-cards/cross-entropy/)（next-token prediction） | 模型預測的下個 token 機率跟真實答案的距離 |
| SFT          | Cross-entropy（同上、但 only on assistant response）                          | 模型回答跟人類示範回答的距離              |
| Reward model | Pairwise ranking loss                                                         | 「人類偏好 A 大於 B」這個訊號的擬合度     |
| RLHF / DPO   | KL-constrained reward loss / DPO loss                                         | reward 高 + 不偏離 base 模型太遠          |

評估時用的指標（[perplexity](/llm/knowledge-cards/perplexity/)、accuracy、BLEU 等）跟訓練 loss 是不同概念：loss 是「訓練要 minimize 的東西」、指標是「給人看模型好不好的數字」、兩者不一定一致（loss 降但指標不一定升、反之亦然）。

## 設計責任

選 loss function 等於選「訓練要把模型推往哪個方向」。Cross-entropy 推「機率分佈接近真實 token」、reward model 推「人類偏好高的回應」、DPO 推「偏好回應 vs 拒絕回應的對比」— 每種 loss 對應的模型行為不同。讀 paper 看到「我們用 X loss」、要回問「這 loss 把模型推往哪個方向」、才能判斷模型訓練出來的特性是否符合預期。
