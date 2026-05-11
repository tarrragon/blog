---
title: "2.1 機率與資訊論"
date: 2026-05-11
description: "LLM 輸出的本質是機率分佈：softmax、cross-entropy、KL divergence、perplexity 在訓練與推論中的角色"
tags: ["llm", "math", "probability"]
weight: 1
---

LLM 輸出的本質是「下一個 [token](/llm/knowledge-cards/token/) 的機率分佈」。模型 forward pass 結束後、會對詞彙表中每個 token 給出一個分數（logit）；softmax 把分數轉成合法的機率分佈、之後用各種 sampling 策略挑下一個 token。訓練時用 cross-entropy loss 衡量「模型預測的機率分佈跟真實答案差多少」、最佳化方向就是讓兩者盡量靠近。

本章整理這條鏈上的核心概念。每個概念給出定義、在 LLM 中的位置、實務上會在哪裡遇到。

## 本章目標

讀完本章後、你應該能：

1. 解釋 LLM 輸出層為什麼用 softmax、不用其他正規化方式。
2. 看到 `temperature=0.2` 設定時、知道它在調機率分佈的什麼。
3. 看到 benchmark 報告 perplexity 數字時、知道它衡量什麼。
4. 理解 cross-entropy 為什麼是 LLM 訓練的標準 loss function。

## 機率分佈：把可能性量化

機率分佈（probability distribution）的核心定義是「對所有可能事件指派一個機率值、總和為 1、每個值在 0 到 1 之間」。LLM 中的核心場景：對詞彙表中每個 token 指派一個機率、總和為 1。

詞彙表大小（vocabulary size）通常幾萬到十幾萬：

| 模型         | Vocab Size |
| ------------ | ---------- |
| Llama 3 系列 | 128,256    |
| Gemma 4 系列 | 256,000    |
| GPT-4o       | ~200,000   |
| Qwen3 系列   | 152,064    |

模型最後一層的輸出是「對這 N 個 token 的機率分佈」、N 是 vocab size。每生一個新 token、就 sample 一次這個分佈。

## Logit：softmax 之前的原始分數

Logit 的核心定義是「模型最後一層輸出的原始分數、還沒正規化成機率」。每個 token 對應一個 logit、可以是任意實數（包括負數）。

Logits 的形狀是 `(vocab_size,)`、例如 Gemma 4 的 logits 是長度 256,000 的向量。直接看 logits 沒意義、需要轉成機率分佈才能 sample。

## Softmax：把 logits 轉成機率分佈

Softmax 的核心定義是「把任意實數向量轉成合法的機率分佈」的函式：

```text
softmax(x)ᵢ = exp(xᵢ) / Σⱼ exp(xⱼ)
```

幾何意義：先用 `exp` 把所有 logit 變成正數（強化大值、壓抑負值）、再除以總和讓總和為 1。結果是合法的機率分佈：每個值在 (0, 1) 之間、總和為 1。

為什麼用 softmax 而非其他正規化（如 `xᵢ / Σ xⱼ`）：

1. **處理負數**：直接歸一化遇到負 logit 會壞掉；exp 把所有值變正。
2. **強化對比**：exp 放大差距、讓「最有可能的 token」拿到更大的機率比例。
3. **數學性質好**：softmax 的導數形式漂亮、方便 backprop 計算 gradient。

實務上會在這幾個地方遇到 softmax：

- **輸出層**：把 logits 轉成「下個 token 的機率分佈」。
- **Attention**：把 attention scores（內積結果）轉成「注意力權重分佈」。詳見 [3.2 attention 機制](/llm/03-theoretical-foundations/attention-mechanism/)。

## Temperature：調整分佈的尖銳度

Temperature（溫度）的核心定義是「softmax 之前先除以一個正數、調整輸出分佈的尖銳度」：

```text
softmax_with_temperature(x, T)ᵢ = exp(xᵢ / T) / Σⱼ exp(xⱼ / T)
```

T 對分佈的影響：

| Temperature | 效果                                               |
| ----------- | -------------------------------------------------- |
| T → 0       | 分佈接近 one-hot、永遠選機率最大的 token（greedy） |
| T = 1       | 原始 softmax 分佈                                  |
| T → ∞       | 分佈接近 uniform、每個 token 機率接近相等          |

實務經驗：

- 寫 code 場景用 T = 0.2 ~ 0.4、讓回答穩定、減少 hallucination。
- 創意寫作用 T = 0.7 ~ 1.0、保留多樣性。
- 確定性場景（測試、reproducible 評估）用 T = 0。

LM Studio 跟其他推論伺服器的 temperature 設定背後就是這個公式。

## Top-K 與 Top-P sampling

Sampling 策略決定「從機率分佈挑下一個 token」的具體方法。主流選擇：

| 策略            | 機制                                    | 適合場景                       |
| --------------- | --------------------------------------- | ------------------------------ |
| Greedy          | 永遠選機率最大的                        | 確定性、reproducible 評估      |
| Beam search     | 同時保留 K 個候選序列、選累積機率最大的 | 翻譯、摘要等需要全局最佳的場景 |
| Top-K           | 只考慮機率最大的 K 個 token、其餘設 0   | 控制多樣性下界                 |
| Top-P (nucleus) | 只考慮機率累積 ≤ P 的 token 子集        | 動態調整候選數、目前最常見     |

Top-P sampling 的細節：先依機率排序、累加直到超過閾值 P（如 0.9）、只 sample 這些 token、其他丟掉。Token 多樣性自動依分佈尖銳度調整、比固定 K 彈性。

詳細展開見 [3.5 sampling 策略](/llm/03-theoretical-foundations/sampling-and-decoding/)。

## Cross-Entropy：訓練 LLM 的 loss function

Cross-entropy（交叉熵）的核心定義是「衡量兩個機率分佈的差距」。形式：

```text
H(p, q) = -Σᵢ p(xᵢ) log q(xᵢ)
```

p 是真實分佈、q 是模型預測分佈。LLM 訓練時、p 是 one-hot（正確 token 機率 1、其他 0）、q 是模型 softmax 輸出。Cross-entropy loss 簡化為：

```text
loss = -log(q(正確 token))
```

幾何意義：模型給正確 token 的機率越高、loss 越低。完美預測時 loss → 0、完全錯時 loss → ∞。

為什麼用 cross-entropy 而非其他 loss：

1. **跟 softmax 配合好**：兩者組合的 gradient 形式漂亮、訓練穩定。
2. **直接最佳化機率**：跟模型輸出的本質一致、不用引入額外轉換。
3. **資訊論依據**：cross-entropy 等於「假設真實分佈是 p、用 q 編碼平均要多少 bits」。

## Perplexity：模型品質的標準指標

Perplexity（困惑度）的核心定義是「e 的 cross-entropy 次方」、衡量模型預測下一個 token 的不確定性：

```text
perplexity = exp(cross-entropy)
```

幾何意義：「平均來說、模型猶豫在幾個 token 之間」。

- Perplexity = 10：模型平均要在 10 個 token 中挑、不確定性中等。
- Perplexity = 2：模型很有信心、平均在 2 個 token 中挑。
- Perplexity = vocab_size：模型完全沒學到、隨機猜。

實務上 perplexity 是預訓練模型品質的標準評估指標。GPT-3 paper 報告各種任務的 perplexity；本地模型對比常引用 WikiText / C4 等 benchmark 上的 perplexity 數字。

Perplexity 跟 [SWE-bench](/llm/knowledge-cards/swe-bench/) 等任務 benchmark 是兩個維度：前者衡量「模型預測下一個 token 的不確定性」、後者衡量「實際解問題的能力」。能力強的模型 perplexity 通常較低、但不是線性關係。

## KL Divergence：兩個分佈的距離

KL divergence（Kullback-Leibler divergence、KL 散度）的核心定義是「衡量分佈 q 偏離分佈 p 的程度」：

```text
KL(p || q) = Σᵢ p(xᵢ) log(p(xᵢ) / q(xᵢ))
```

性質：

- KL(p || q) ≥ 0、等號成立當且僅當 p = q。
- **不對稱**：KL(p || q) ≠ KL(q || p) 一般而言。
- 跟 cross-entropy 關係：`H(p, q) = H(p) + KL(p || q)`、其中 H(p) 是 p 自身的 entropy。

LLM 中 KL divergence 的用途：

- **RLHF**：把 fine-tune 後的模型機率分佈跟原 pre-trained 模型對齊、避免 fine-tune 過頭偏離原模型太多。
- **Knowledge distillation**：把大模型的分佈傳給小模型、小模型最小化 KL(大模型 || 小模型)。
- **DPO / 各種 alignment 方法**：用 KL constraint 控制 policy 偏移量。

## Entropy：分佈的不確定性

Entropy（熵）的核心定義是「機率分佈本身的不確定性」：

```text
H(p) = -Σᵢ p(xᵢ) log p(xᵢ)
```

幾何意義：「平均來說、用 p 編碼一個 sample 要多少 bits」。

- 確定分佈（one-hot）：entropy = 0、沒有不確定性。
- Uniform 分佈：entropy = log(N)、最大不確定性。

Entropy、cross-entropy、KL divergence 三者關係：

```text
H(p, q) = H(p) + KL(p || q)
```

Cross-entropy 等於「真實分佈的 entropy」加上「模型預測偏離真實的 KL distance」。訓練 LLM 是最小化 H(p, q)、等同於最小化 KL(p || q)、因為 H(p) 是常數（資料本身的不確定性）。

## 小結

LLM 輸出端的數學鏈是「logit → softmax → 機率分佈 → sampling」、訓練端的鏈是「預測分佈跟真實 one-hot 的 cross-entropy → gradient → 更新權重」。理解這條鏈、各種推論參數（temperature、top-k、top-p）跟訓練概念（loss、perplexity、KL constraint）就能落到正確位置。

想看完整資訊論推導（Shannon's coding theorem、mutual information 等）、見 [2.4 公開課推薦](/llm/02-math-foundations/going-deeper-math/) 的 MIT 6.050J / Stanford EE376A 等資源。

下一章：[2.2 微積分與最佳化](/llm/02-math-foundations/calculus-and-optimization/)。
