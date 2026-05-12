---
title: "Test-Time Compute"
date: 2026-05-12
description: "推論時動態增加計算量換取答案品質的 paradigm、reasoning model 跟 best-of-N 的共同基底"
weight: 1
tags: ["llm", "knowledge-cards", "reasoning", "inference"]
---

Test-time compute（推論時計算）的核心概念是「**在推論階段花更多計算量、換取更高品質的答案**」、不是只在訓練時投入算力。是 2024-2026 LLM 的 paradigm shift：GPT-3 → GPT-4 主要靠「更大模型 + 更多訓練資料」；o1 / DeepSeek-R1 → 主要靠「同模型、推論時想更久」。

## 概念位置

LLM 算力分配的兩條軸：

```text
Training compute（訓練算力）：
  pre-training 大量 GPU-hour → 模型參數
  一次性投入、後續推論不變
  → GPT-3 → 4 的主要 paradigm

Test-time compute（推論算力）：
  每次推論時、視任務難度動態增加算力
  難題想 30 秒（生 5000 token reasoning trace）
  簡單問題 1 秒結束（直接答）
  → o1 / R1 / Claude thinking 的新 paradigm
```

Test-time compute 的常見實作形式：

| 形式                                                            | 機制                                                             | 代表                                       |
| --------------------------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------ |
| [Chain-of-thought](/llm/knowledge-cards/chain-of-thought/) 內建 | 模型訓練成「自然」用長 reasoning trace、直接生 thinking + answer | o1、DeepSeek-R1、Qwen-QwQ、Claude thinking |
| Best-of-N sampling                                              | 同 prompt 跑 N 次、reward model 選最好的                         | OpenAI early experiments、verifier-based   |
| Tree search                                                     | 結構化探索多條 reasoning path                                    | AlphaCode、tree of thoughts                |
| Self-consistency                                                | 多次 sample reasoning、投票選最常見答案                          | 早期 CoT prompting 技巧                    |
| Tool use + verification                                         | 模型呼叫 calculator / interpreter 驗證自己                       | Coding agent、math 解題 agent              |

DeepSeek-R1 paper 顯示「reasoning trace 長度跟 benchmark 表現正相關、可透過 RL 拉長」— 把 test-time compute 變成可訓練、可 scale 的維度。

## 設計責任

讀 paper / benchmark 看到「pass@1 vs pass@10」「budget tokens」「thinking time」等就跟 test-time compute 相關。寫 code 場景的判讀：

1. **Reasoning model 算成本翻倍**：同一個 prompt、reasoning model 生 5000 token thinking + 500 token answer、傳統 model 直接生 500 token answer、推論成本差 ~10 倍
2. **本地跑 reasoning model 的痛點**：需要長 [context window](/llm/knowledge-cards/context-window/) 容納 thinking trace、生成時間長
3. **適用任務挑選**：複雜 reasoning（math、debug、long horizon planning）值得花 test-time compute；簡單任務（autocomplete、查詢）不值得
4. **混用策略**：日常用 instruct model、困難任務切到 reasoning model、是個人 dev 常見模式
