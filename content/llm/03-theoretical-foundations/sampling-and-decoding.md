---
title: "3.5 Sampling 與 Decoding 策略"
date: 2026-05-11
description: "Greedy、beam search、top-k、top-p、temperature、min-p：模型輸出後怎麼挑下一個 token"
tags: ["llm", "theory", "sampling"]
weight: 5
---

LLM 的輸出本質是「下一個 [token](/llm/knowledge-cards/token/) 的機率分佈」、不是直接的 token。從機率分佈挑下一個 token 的具體方法、就是 sampling / decoding 策略。同一個模型、同一個 prompt、不同 sampling 策略會給出顯著不同的輸出。

本章拆開主流 sampling 策略的機制、各自適合的場景、以及 `temperature`、`top_p` 這些常見參數在這條鏈上的位置。

## 本章目標

讀完本章後、你應該能：

1. 解釋 `temperature=0` 跟 `temperature=0.8` 的具體差別。
2. 區分 top-k、top-p、min-p 三者的機制。
3. 看到 `repetition_penalty=1.1` 設定時、知道它解什麼問題。
4. 解釋為什麼確定性測試要設 `temperature=0` + `seed`。

## 從 logits 到下個 token

複習一下 LLM 輸出端的鏈：

```text
final hidden states → output projection → logits → temperature → softmax → 機率分佈
→ sampling 策略 → 下個 token
```

各環節在 sampling 中的位置：

| 環節                  | 對 sampling 的影響                        |
| --------------------- | ----------------------------------------- |
| logits                | 模型給每個 token 的原始分數、還沒正規化   |
| temperature           | 在 softmax 前除以 T、調整分佈尖銳度       |
| softmax               | 把 logits 轉成機率分佈                    |
| top-k / top-p / min-p | 過濾低機率 token、把候選集縮小            |
| 重新正規化            | 把過濾後的剩餘 token 重新正規化成機率分佈 |
| 取樣                  | 從正規化分佈中隨機選一個 token            |
| repetition penalty    | 對已出現的 token 降權、避免重複           |

實際參數順序視推論伺服器實作而異、但概念上是這條鏈。

## Greedy Decoding：永遠選機率最大

Greedy decoding 的核心定義是「每步選 softmax 後機率最大的 token」：

```text
next_token = argmax(probabilities)
```

特性：

- **確定性**：同 prompt 永遠生同樣輸出。
- **快**：不用 sampling、不用算 cumulative probabilities。
- **缺點**：傾向選最常見 pattern、輸出單調；常陷入 repetition loop。

實務用途：

- **Reproducible 評估**：跑 benchmark、自動測試。
- **單元測試**：確保模型輸出可預測。
- **某些 reasoning chain**：選最有信心的下一步。

效果上等同 `temperature=0`、許多推論伺服器把兩者當同義詞。

## Beam Search：保留 top-K 條候選序列

Beam search 的核心想法是「每步保留累積機率最大的 K 條序列、每條繼續展開、最後選整體機率最高的」。K 叫 beam size。

| Beam size | 行為                     |
| --------- | ------------------------ |
| 1         | 等同 greedy              |
| 3 ~ 5     | 翻譯、摘要等任務常用     |
| 10+       | 高品質生成、但計算成本高 |

特性：

- **全局較優**：不只看當步、考慮整段序列。
- **適合「有正確答案」的任務**：翻譯、摘要、code 生成。
- **缺點**：對 open-ended 生成（聊天、創意寫作）會 collapse 到平庸、缺乏多樣性。

Chat / 對話場景多半不用 beam search、用 sampling 策略保留多樣性。

## Temperature：調分佈尖銳度

Temperature 的機制在 [模組二 2.1](/llm/02-math-foundations/probability-and-information/) 已經詳細展開。簡單回顧：

```text
adjusted_logits = logits / temperature
probabilities = softmax(adjusted_logits)
```

| Temperature | 效果                                      |
| ----------- | ----------------------------------------- |
| 0           | 等同 greedy（argmax）                     |
| 0.2 ~ 0.4   | 寫 code、回答事實問題、減少 hallucination |
| 0.7         | 預設、平衡多樣性與品質                    |
| 0.9 ~ 1.0   | 創意寫作、保留多樣性                      |
| > 1.5       | 隨機性極高、輸出可能變混亂                |

實務經驗：

- 寫 code 場景設 0.2 ~ 0.4 較穩。
- 創意任務（寫故事、brainstorming）設 0.8 ~ 1.0。
- Reproducible 測試設 0 + 固定 seed。

## Top-K Sampling

Top-K sampling 的核心定義是「只考慮機率最大的 K 個 token、其他設 0、重新正規化後取樣」：

```text
1. 對機率排序、取最大的 K 個。
2. 其他設 0。
3. 重新正規化（讓總和為 1）。
4. 從正規化分佈取樣。
```

K 控制候選範圍：

| K    | 行為                        |
| ---- | --------------------------- |
| 1    | 等同 greedy                 |
| 40   | 預設常用值                  |
| 100+ | 接近完全 sampling、限制較小 |

缺點：K 是固定值、無法適應分佈尖銳度。當分佈尖銳時（一個 token 機率 90%）、K=40 包括很多近 0 機率的雜訊；當分佈平坦時（每個 token 機率 1%）、K=40 過於限制。

## Top-P / Nucleus Sampling

Top-P sampling（也叫 nucleus sampling、Holtzman et al., 2019）的核心想法是「動態決定候選集大小」：

```text
1. 對機率從大到小排序。
2. 從大到小累加、直到累積機率 ≥ P（如 0.9）。
3. 只保留這些 token、其他設 0。
4. 重新正規化、取樣。
```

例：

- 分佈尖銳（一個 token 機率 95%）：P=0.9 可能只選 1 ~ 2 個 token。
- 分佈平坦（top 10 各 5%）：P=0.9 可能選 15 ~ 20 個 token。

P 的常用值：

| P    | 行為                       |
| ---- | -------------------------- |
| 0.5  | 較保守、傾向選機率高的     |
| 0.9  | 預設、保留合理多樣性       |
| 0.95 | 略放寬                     |
| 1.0  | 等同關閉 top-p、用完整分佈 |

Top-P 是現代 LLM 的主流 sampling 策略、比 top-K 彈性。多數推論伺服器預設 top_p=0.9。

## Min-P：新興 sampling 策略

Min-P sampling（2024 ~）的核心想法是「設一個機率閾值、最大機率 token × P_min 以下的全部去掉」：

```text
1. 找出最大機率 p_max。
2. 閾值 = p_max × P_min（如 0.1）。
3. 機率 < 閾值的 token 全部設 0、重新正規化。
```

特性：

- 自動適應分佈尖銳度（用比例而非絕對值）。
- 比 top-P 更穩定、近一兩年在開源社群興起。
- LM Studio、llama.cpp 等支援。

P_min 常用值：

| P_min | 行為       |
| ----- | ---------- |
| 0.05  | 保留多樣性 |
| 0.1   | 平衡       |
| 0.2   | 較保守     |

## Repetition Penalty

Repetition penalty 的核心想法是「對已出現的 token 降低機率、避免無限重複」：

```text
adjusted_logit(token) = logit(token) / repetition_penalty   if token 已出現
                      = logit(token)                          if token 沒出現
```

P 大於 1 時、已出現 token 的 logit 被降低、後續 sampling 較難選到。

| Penalty | 效果                           |
| ------- | ------------------------------ |
| 1.0     | 關閉                           |
| 1.05    | 輕微抑制                       |
| 1.1     | 預設常用                       |
| 1.3+    | 強烈抑制、可能過度避免合理重複 |

代價：寫 code 場景下、`if`、`for`、`return` 等關鍵字常出現、太高的 repetition penalty 會壞掉 code。寫 code 場景 penalty 設低（1.0 ~ 1.05）或關閉。

## Seed：固定 sampling 的隨機性

Sampling 用 random number generator 取樣。**設定 seed 讓 RNG 確定性**、相同 prompt + 相同 seed 給相同輸出：

```python
{
  "temperature": 0.7,
  "top_p": 0.9,
  "seed": 42
}
```

實務用途：

- **Reproducible 評估**：跑 benchmark 要可重複。
- **A/B 測試**：對比不同 prompt 在同 seed 下的差異。
- **Debug**：重現一個錯誤輸出。

注意：seed 不是所有伺服器都支援、OpenAI API 是 best-effort（同 seed 不保證完全一致）、本地伺服器多半支援嚴格 seed 控制。

## Logit Bias：強制 / 排除特定 token

Logit bias 的機制是「對特定 token 的 logit 加減一個固定值」：

```text
adjusted_logit(token) = logit(token) + bias(token)
```

用途：

- **強制特定 token**：bias = +100、softmax 後機率近 1。
- **完全禁止**：bias = -100、softmax 後機率近 0。
- **微調傾向**：bias = ±5、輕微傾斜。

實務用例：

- 強制輸出 JSON 格式：對 `{` 加 bias 在開頭。
- 避免特定詞：對敏感詞加負 bias。
- 約束輸出：限制只能用特定 vocabulary。

OpenAI、Ollama 等多數推論伺服器支援 logit_bias 參數。

## Structured Output / Constrained Decoding

Structured output 的核心想法是「sampling 時加 grammar 約束、強制輸出符合特定結構（JSON、SQL、regex 等）」。實作方法：

- **JSON mode**：每步只允許「能讓 JSON 仍合法」的 token。
- **Grammar-based**：用 BNF / lark / etc. 定義語法、sampling 時 reject 違反語法的 token。
- **Token mask**：依當前狀態決定哪些 token 合法、不合法的 logit 設 -∞。

實務工具：

- llama.cpp 的 `grammar` 參數。
- Outlines、LMQL 等 framework。
- OpenAI 的 `response_format: { type: "json_schema" }`。

寫 code 場景中、structured output 對「要可解析的輸出」（如 commit message 格式、structured API call）很有用。

## Decoding 策略對體感的影響

下表是寫 code 場景下、不同 decoding 配置的體感：

| 配置                                    | 體感                              |
| --------------------------------------- | --------------------------------- |
| temperature=0、greedy                   | 確定、可重複、但可能單調          |
| temperature=0.2、top_p=0.95             | 穩定、寫 code 主流                |
| temperature=0.7、top_p=0.9              | 平衡、預設                        |
| temperature=1.0、top_p=0.95、min_p=0.05 | 創意、多樣                        |
| temperature=1.5                         | 過於隨機、code 容易壞             |
| repetition_penalty=1.3、寫 code 場景    | 抑制太強、會壞掉 keyword 重複用法 |

實務建議：寫 code 場景下 temperature=0.2 ~ 0.4、top_p=0.9 ~ 0.95、其他保留預設就好。Continue.dev 等 IDE 整合多半自動調整。

## 小結

從機率分佈挑下一個 token、是 LLM 輸出端的最後一步。Temperature 調分佈尖銳度、top-k / top-p / min-p 過濾低機率候選、repetition penalty 避免重複、seed 控制確定性。各策略可組合、寫 code 場景下「temperature=0.2 ~ 0.4 + top_p=0.9」是穩健預設。

下一章：[3.6 tokenization 算法](/llm/03-theoretical-foundations/tokenization-algorithms/)、補完 input / output 端的細節。
