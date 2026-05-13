---
title: "LLM-as-Judge"
date: 2026-05-12
description: "用 LLM 評估另一個 LLM 的輸出品質、production eval 的主流方法、500-5000× 成本降但有 bias 要處理"
weight: 1
tags: ["llm", "knowledge-cards", "evaluation", "production"]
---

LLM-as-Judge 的核心概念是「**用一個 LLM（judge）對另一個 LLM（test subject）的輸出做品質評估**」。給 judge 一個 rubric（評分標準）跟 (input, output) pair、judge 輸出分數或 pairwise 偏好。是 production LLM eval 的主流方法（500-5000× 比 human eval 便宜、80%+ 跟人類同意度）、但有 bias 要處理（position / verbosity / self-preference）。

## 概念位置

跟其他 eval 路徑的對比：

| Eval 路徑                                                                         | 成本                   | 速度                  | 適合                                    |
| --------------------------------------------------------------------------------- | ---------------------- | --------------------- | --------------------------------------- |
| Standard [benchmark](/llm/knowledge-cards/llm-benchmarks/)（MMLU / SWE-bench 等） | 中                     | 慢（一次 run 數小時） | 通用能力比較                            |
| Human eval                                                                        | 極高（每筆 $1-10）     | 慢                    | 黃金標準、final QA                      |
| **LLM-as-Judge（本卡）**                                                          | 低（每筆 $0.001-0.01） | 快                    | Production loop eval、自己應用 in-house |
| Rule-based / regex                                                                | 極低                   | 即時                  | 明確 binary（如格式對不對）             |

主要 use case：

1. **In-house benchmark**：自己工作流的真實案例、自寫 rubric、judge 評
2. **Production trace eval**：用 [LLM tracing](/llm/knowledge-cards/llm-tracing/) 蒐集的 production trace、定期 judge 跑、抓品質回歸
3. **A/B test**：兩個 prompt / model 變體、judge 做 pairwise 比較
4. **Synthetic data quality**：用大模型生 fine-tune 資料、judge 過濾低品質

## 設計責任

讀 eval framework / production AI app 看到「LLM as judge」「pairwise eval」「LLM evaluator」就是這 framing。寫 code 場景的判讀：

1. **Judge 模型選擇**：強模型當 judge（GPT-5 / Claude 4 / Gemini 旗艦）、reasoning model 更穩；judge 跟被測同家可能有 self-preference bias
2. **三大 bias 緩解**：
   - **Position bias**：A/B pairwise 換位置跑 2 次取一致 vote
   - **Verbosity bias**：rubric 加「冗長不加分」明確指示、或長度 normalize
   - **Self-preference bias**：用 3 個不同 judge model 取多數
3. **跟 [4.21 LLM-as-judge 章節](/llm/04-applications/llm-as-judge/) 的關係**：本卡是定義、章節是工程實務（rubric design、bias 緩解、calibration、trace 串接）
4. **不是萬靈丹**：高 stake 任務（醫療、法律、安全）仍需 human eval；judge 的天花板 = judge 模型本身的能力
