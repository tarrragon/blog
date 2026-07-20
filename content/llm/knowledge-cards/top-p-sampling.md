---
title: "Top-K / Top-P / Min-P Sampling"
date: 2026-05-12
description: "從機率分佈取樣前先過濾低機率 token 的三種策略、現代 LLM 推論主流"
weight: 1
tags: ["llm", "knowledge-cards", "sampling", "decoding"]
---

Top-K、Top-P（nucleus sampling）、Min-P 的核心概念是「**從 [softmax](/llm/knowledge-cards/softmax/) 出來的機率分佈中、先過濾掉低機率 token、再從剩餘候選隨機取樣**」。三者是 LLM 對話 / 寫 code 場景的主流 sampling 策略、跟 greedy 對比保留隨機多樣性、跟 [beam search](/llm/knowledge-cards/beam-search/) 對比計算成本低。

## 概念位置

三種策略的篩選方式：

| 策略      | 機制                                                  | 直覺                         |
| --------- | ----------------------------------------------------- | ---------------------------- |
| **Top-K** | 只保留機率前 K 個 token、其餘設 0                     | 固定候選數量、簡單           |
| **Top-P** | 把 token 依機率排序、保留「累積機率達到 P」的最小集合 | 動態候選數量、適應分佈尖銳度 |
| **Min-P** | 只保留機率 ≥ (P × max_probability) 的 token           | 相對閾值、避免低品質 token   |

範例（vocab 前 10 個 token 的機率）：

```text
token:     A     B     C     D     E     F     G     H     I     J
prob:    0.45  0.30  0.12  0.05  0.03  0.02  0.01  0.01  0.005 0.005

Top-K=3：保留 A、B、C（前 3 個）
Top-P=0.9：累積機率達 0.9、保留 A、B、C、D（0.45+0.30+0.12+0.05 = 0.92）
Min-P=0.1：max=0.45、閾值=0.045、保留 A、B、C、D（≥ 0.045）
```

三者實務上常組合使用（如 `top_k=40, top_p=0.9, temperature=0.7`）、各自處理不同形狀的分佈，都屬於推論階段的 [sampling constraint](/llm/knowledge-cards/sampling-constraint/)。

| 參數情境                 | 適合策略                                              |
| ------------------------ | ----------------------------------------------------- |
| 分佈非常尖（模型很確定） | Top-P / Min-P 動態縮小、Top-K 可能太大                |
| 分佈平（模型不確定）     | Top-K 限制最大候選、避免取到極低品質 token            |
| 寫 code / 嚴謹任務       | 低 temperature (0.2 ~ 0.5) + 較緊的 Top-P (0.8 ~ 0.9) |
| 創意 / 多樣寫作          | 高 temperature (0.7 ~ 1.0) + 寬鬆的 Top-P (0.95+)     |

## 設計責任

讀 inference config / Continue.dev 設定看到 `top_k`、`top_p`、`min_p`、`temperature` 就是這組參數。寫 code 場景的判讀：嚴謹任務（code generation、structured output）用低 temperature + 緊 Top-P 取「最可能對的少數 token」；創意 / 對話用高 temperature + 寬 Top-P 取多樣性。Min-P 是 2023 後流行的新策略、實務上比 Top-P 更穩、避免「分佈很尖時 Top-P 仍納入長尾低品質 token」的問題。
