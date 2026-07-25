---
title: "DPO（Direct Preference Optimization）"
date: 2026-05-12
description: "RLHF 的簡化替代：跳過 reward model、直接從人類偏好資料 fine-tune LLM"
weight: 1
tags: ["llm", "knowledge-cards", "training", "alignment"]
---

DPO（Direct Preference Optimization、直接偏好最佳化）的核心概念是「**用人類偏好資料直接 fine-tune LLM、不訓 reward model、不用 RL**」。Rafailov et al. (2023) 提出、用數學變形把 [RLHF](/llm/knowledge-cards/rlhf/) 的「reward model + PPO」兩階段合併成單一個 supervised loss、訓練流程大幅簡化。

## 概念位置

DPO vs [RLHF](/llm/knowledge-cards/rlhf/) 的對比：

| 維度              | RLHF                                        | DPO                                             |
| ----------------- | ------------------------------------------- | ----------------------------------------------- |
| 需要 reward model | 是                                          | 否                                              |
| 訓練步驟          | 收偏好 → 訓 RM → PPO                        | 收偏好 → 直接 DPO loss fine-tune                |
| 訓練穩定性        | PPO 對 hyperparameter 敏感、容易不穩        | 像 supervised learning、相對穩                  |
| 記憶體            | 三個模型同時運作（policy / RM / reference） | 兩個（policy / reference frozen）               |
| KL 約束           | 顯式加 β × KL term                          | 內嵌在 loss 公式裡、不用顯式                    |
| 流行度（2026）    | 商業大廠（OpenAI / Anthropic）              | 開源社群（Llama / Qwen / Gemma 系列許多用 DPO） |

DPO 的 loss 形式（簡化）：

```text
loss = -log σ( β · (log π(y_w|x)/π_ref(y_w|x) - log π(y_l|x)/π_ref(y_l|x)) )
                └─ 偏好 response 在 policy 跟 ref 的 ratio ─┘
                                                            └─ 拒絕 response 的同樣 ratio ─┘
```

直覺：讓 policy 對偏好 response 的機率增加（相對 ref）、對拒絕 response 的機率降低（相對 ref）。

## 設計責任

讀開源 LLM 的 paper / model card 看到「DPO-tuned」「preference fine-tuning」就是這個流程。實務上 DPO 訓練成本只是 RLHF 的一小部分、許多 fine-tune 平台（如 Hugging Face TRL）內建支援。後續還有 IPO、KTO、ORPO 等變體、都是「直接用偏好 fine-tune、不訓 reward」這條路線的進一步演化。
