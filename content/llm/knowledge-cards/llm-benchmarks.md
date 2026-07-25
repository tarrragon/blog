---
title: "LLM Benchmarks（MMLU / HumanEval / SWE-bench 等）"
date: 2026-05-12
description: "LLM 能力評估的標準 benchmark 集合：MMLU / HumanEval / MBPP / SWE-bench / MT-Bench 等的覆蓋範圍與失效情境"
weight: 1
tags: ["llm", "knowledge-cards", "evaluation", "benchmark"]
---

LLM benchmarks 的核心概念是「**用標準化任務集合衡量 LLM 各維度能力的評估工具**」。不同 benchmark 衡量不同維度（知識、reasoning、code、對話、math 等）、選錯 benchmark 看模型會誤判。本卡列主流 benchmark 跟它們的覆蓋面、失效情境，是判讀 [model card](/llm/knowledge-cards/model-card/) 上 benchmark 數字時的對照表。

## 概念位置

主流 LLM benchmark 一覽：

| Benchmark                                        | 衡量維度                   | 任務形式                             | 失效情境                                      |
| ------------------------------------------------ | -------------------------- | ------------------------------------ | --------------------------------------------- |
| **MMLU**                                         | 通用知識（57 學科多選題）  | 4 選 1 選擇題                        | 訓練資料污染（題目可能在 pretrain corpus）    |
| **GSM8K**                                        | 小學數學 word problem      | 文字 + 數字、需 reasoning            | 飽和（前沿模型 95%+）                         |
| **MATH**                                         | 高中 / 競賽數學            | 自由作答                             | 訓練污染、reasoning model 表現遠超 instruct   |
| **HumanEval**                                    | Python function 補完       | 寫一個 function 通過 unit test       | 飽和、僅覆蓋初級 coding                       |
| **MBPP**                                         | Python coding 任務         | 同上、規模較大                       | 同 HumanEval                                  |
| [**SWE-bench**](/llm/knowledge-cards/swe-bench/) | 真實 GitHub issue 修復     | 給 repo + issue、生 patch、跑 test   | 仍是 LLM 主要 coding 差距、不易飽和           |
| **MT-Bench**                                     | 多輪對話品質               | 80 題 prompt、LLM-as-judge 評分      | LLM-as-judge bias、judge 模型本身能力影響評分 |
| **Chatbot Arena**                                | 開放對話偏好（眾人投票）   | A/B 對戰、Elo 排名                   | 文化偏好、prompt 設計影響                     |
| **HELM**                                         | 多 dimension comprehensive | 22 scenarios × 多 metrics            | 計算昂貴、不易追蹤每代新模型                  |
| **AlpacaEval**                                   | 指令跟隨能力               | LLM-as-judge 對比 GPT-4              | Judge bias、易被「verbose」攻擊               |
| **RULER**                                        | Long context 真實任務      | Multi-needle、aggregation、reasoning | 較新、覆蓋仍在演化                            |

> **事實查核註**：各 benchmark 的飽和狀態、前沿模型 score 持續變動、上述為 2026/5 主流觀察。引用前以 [Papers with Code](https://paperswithcode.com/) 或 [HuggingFace Open LLM Leaderboard](https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard) 當前狀態為準。

## Benchmark 的常見陷阱

1. **訓練資料污染（Contamination）**：benchmark 題目本身在 pretrain corpus 出現過、模型「記得」答案、看似強實際是 memorization
2. **飽和（Saturation）**：前沿模型 score 接近上限、無法區分模型品質差距（HumanEval 80%→95% 看似進步、實際 5% 多半是 lucky 而非實質提升）
3. **LLM-as-judge bias**：用 LLM（如 GPT-4）評其他 LLM、judge 的偏好（如「冗長 = 好」）會 bias 評分
4. **Single-task overfitting**：模型廠商針對 benchmark 特別 fine-tune、benchmark 高分但通用能力沒提升
5. **Prompt sensitivity**：同個 benchmark 用不同 prompt format、score 差幾個百分點

## 設計責任

讀 model card / paper 看到 benchmark 數字、判讀框架：

1. **看 multiple benchmarks、不只一個**：如挑 coding 模型、看 HumanEval + MBPP + SWE-bench、不只看 HumanEval
2. **跟自己任務對齊的 benchmark 才重要**：你做 RAG 應用、看 retrieval benchmark；你做 chat、看 MT-Bench / Arena
3. **看「相對」、不只看「絕對」**：「Model A 在 MMLU 比 Model B 高 2%」可能 noise；「A 比 B 高 10%」更可信
4. **In-house benchmark 是最後檢驗**：自己的真實工作流案例 > 任何公開 benchmark
