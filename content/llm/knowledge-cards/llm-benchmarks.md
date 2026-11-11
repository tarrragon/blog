---
title: "LLM Benchmarks（MMLU / HumanEval / SWE-bench 等）"
date: 2026-05-12
description: "LLM 能力評估的標準 benchmark 集合：MMLU / HumanEval / MBPP / SWE-bench / MT-Bench 等的覆蓋範圍與失效情境"
weight: 1
tags: ["llm", "knowledge-cards", "evaluation", "benchmark"]
---

LLM benchmarks 的核心概念是「**用標準化任務集合衡量 LLM 各維度能力的評估工具**」。不同 benchmark 衡量不同維度（知識、reasoning、code、對話、math 等）、選錯 benchmark 看模型會誤判。本卡列主流 benchmark 跟它們的覆蓋面、失效情境，是判讀 [model card](/llm/knowledge-cards/model-card/) 上 benchmark 數字時的對照表。

## 跟其他概念的關係

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

## 判斷條件與後果

model card 或 paper 上的 benchmark 分數是否能拿來選模型，看三個條件：分數來自幾個 benchmark、benchmark 量的維度是否對得上自己的任務、兩個模型的差距是否大過雜訊。

只看單一 benchmark 時（挑 coding 模型只看 HumanEval），高分可能來自〈Benchmark 的常見陷阱〉裡的飽和、訓練資料污染或針對那一組題目的 fine-tune，分數反映的是對單一題組的適配；HumanEval、MBPP 與 SWE-bench 都高時，比較可能是 coding 能力本身。benchmark 量的維度跟自己的任務不同時（做 RAG 應用卻看對話的 MT-Bench），分數高低跟自己的應用沒有關係，做 RAG 對照的是 retrieval 類 benchmark，做 chat 對照的是 MT-Bench 或 Arena。兩個模型在同一個 benchmark 只差幾個百分點時（MMLU 差 2%），換一種 prompt format 就可能造成同樣大的差距（prompt sensitivity），這個差距分不出高下；差到 10% 這個量級才比較可信。公開 benchmark 都量不到自己工作流的資料與格式，所以最後的檢驗是用自己真實案例做的 in-house benchmark。
