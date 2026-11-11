---
title: "LLM-as-Judge"
date: 2026-05-12
description: "用 LLM 評估另一個 LLM 的輸出品質、production eval 的主流方法、500-5000× 成本降但有 bias 要處理"
weight: 1
tags: ["llm", "knowledge-cards", "evaluation", "production"]
---

LLM-as-Judge 的核心概念是「**用一個 LLM（judge）對另一個 LLM（test subject）的輸出做品質評估**」。給 judge 一個 rubric（評分標準）跟 (input, output) pair、judge 輸出分數或 pairwise 偏好。是 production LLM eval 的主流方法（跟標準 [LLM benchmark](/llm/knowledge-cards/llm-benchmarks/) 互補、500-5000× 比 human eval 便宜、80%+ 跟人類同意度）、但有 bias 要處理（position / verbosity / self-preference）。

## 跟其他概念的關係

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

## 判斷條件與後果

LLM-as-Judge 的分數可信到什麼程度，取決於 judge 模型的能力，以及 judge 帶進評分的三種 bias：

- **judge 的能力不及被測模型時**：rubric 的每一項都由 judge 自己判定，所以分數的天花板就是 judge 模型本身的能力，被測輸出裡 judge 看不出的錯誤不會反映在分數上。高 stake 任務（醫療、法律、安全）因此仍保留 human eval 當最終檢查。
- **pairwise 比較只跑一種排列時**：position bias 讓固定位置的回應多拿偏好，兩個變體的勝負混進了位置效應；A/B 換位置各跑一次、只採兩次一致的判定，位置效應就被抵銷。
- **rubric 沒有處理回應長度時**：verbosity bias 讓較長的回應拿高分，分數同時反映品質與長度；rubric 寫明冗長不加分，或先把長度 normalize，這一項才從分數裡拿掉。
- **judge 與被測模型同一家時**：self-preference bias 讓 judge 偏好自家模型的輸出，跨廠牌比較的結果偏向 judge 那一家；改用幾個不同家的 judge 取多數，各家的偏好不再朝同一個方向。

rubric 設計、calibration 與 trace 串接的工程做法在 [4.21 LLM-as-judge 章節](/llm/04-applications/llm-as-judge/)。
