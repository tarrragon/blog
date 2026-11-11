---
title: "Catastrophic Forgetting"
date: 2026-05-12
description: "Fine-tune 模型時、新訓練資料覆蓋掉原本學到的能力的現象、LoRA / 資料 mixing 是主要緩解"
weight: 1
tags: ["llm", "knowledge-cards", "fine-tuning", "training"]
---

Catastrophic forgetting（災難遺忘）的核心概念是「**Fine-tune 模型時、新訓練資料的 [gradient](/llm/knowledge-cards/gradient/) 更新破壞了模型原本學到的能力**」。在 LLM fine-tuning 場景特別常見：在自己 domain 資料上 fine-tune、結果模型在原 benchmark / 通用任務上分數大幅下降。

## 跟其他概念的關係

Catastrophic forgetting 在 LLM fine-tuning 的典型表現：

```text
Before fine-tune（base instruct model）：
  HumanEval: 75
  MMLU: 70
  自己 domain 任務 hit rate: 40%

After fine-tune（在自己 domain 資料上跑 SFT、3 epochs）：
  HumanEval: 55  ← 下降 20 點
  MMLU: 50       ← 下降 20 點
  自己 domain 任務 hit rate: 70%  ← 提升 30 點

→ 自己 domain 強了、但通用能力崩了
```

成因：

1. **[Gradient](/llm/knowledge-cards/gradient/) 在新資料上對 base 權重做大更新**：原本 base 的權重對通用任務有用、被覆蓋掉
2. **資料分佈差距大**：自己 domain 跟 pretrain corpus 分佈差距大、學新的 = 忘舊的
3. **訓練 epoch 太多**：模型 over-fit 到新資料、舊能力衰退更嚴重
4. **Learning rate 太高**：每步更新幅度大、舊權重變化快

## 緩解策略

| 策略                                                                      | 機制                                                       | 適用情境                      |
| ------------------------------------------------------------------------- | ---------------------------------------------------------- | ----------------------------- |
| [LoRA](/llm/knowledge-cards/lora/) / [QLoRA](/llm/knowledge-cards/qlora/) | 凍住 base 權重、只訓 adapter、舊能力完全保留               | 多數 fine-tune 場景的 default |
| 資料 mixing                                                               | 訓練 batch 內 mix 通用資料 + domain 資料、避免分佈完全偏移 | 跟 LoRA 結合使用              |
| Lower learning rate                                                       | 用較小 lr（如 5e-6 vs 1e-5）、減慢更新                     | 全參數 fine-tune 必選         |
| Fewer epochs                                                              | 訓 1-2 epoch 就停、不過度擬合                              | 同上                          |
| Regularization（KL constraint）                                           | Loss 加「不能偏離 base 太遠」的約束                        | RLHF / DPO 已內建             |
| EWC（Elastic Weight Consolidation）                                       | 對重要權重加更強懲罰、防止它們被改                         | 研究用、實務罕見              |

主流 fine-tuning 配置（避免 catastrophic forgetting）：

```text
方法：QLoRA fine-tune
參數：
  - rank: 16-64（看資料量）
  - alpha: 32（typical）
  - lr: 1e-4 ~ 5e-4（LoRA 適合較大 lr）
  - epochs: 1-3（不過度訓）
  - 資料：80% in-domain + 20% 通用 instruction data（保留通用能力）
```

## 判斷條件與後果

讀 fine-tune paper 或報告看到「forgetting」「retention」「regression」，指的就是這個現象。forgetting 是否看得出來、是否會加重，取決於下面幾個條件：

1. **fine-tune 前沒有 baseline benchmark 時**：fine-tune 後的通用分數沒有比較對象，上面那種 domain 分數上升、通用分數下降的組合看不出來。所以 base model 先在通用 benchmark 與自己 domain 上各跑一次，fine-tune 後再比。
2. **選 full fine-tune 時**：所有權重都被新資料的 gradient 更新，是 forgetting 風險最高的配置。LoRA / QLoRA 凍住 base 權重、只訓 adapter，base 學到的能力留在權重裡，這是它成為多數場景預設的原因。
3. **fine-tune 後模型只答得出自己 domain 的問題、不再能一般對話時**：通用 chat 能力已經被覆蓋，forgetting 過頭了。
4. **在已經 fine-tune 過的模型上再 fine-tune 時**（如 SFT 之後接 DPO）：每一輪都可能再偏離一次，forgetting 風險疊加，每一輪之後都要重跑 baseline 比對。
5. **模型的能力來自後期訓練時**：reasoning 是後期訓練出來的，一輪 SFT 就容易破壞它，所以 reasoning model 不建議再 fine-tune。
