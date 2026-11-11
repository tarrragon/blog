---
title: "Active Parameter"
date: 2026-05-12
description: "MoE 模型每生成一個 token 實際參與計算的參數量、跟模型總參數量不同、影響推論速度上限"
weight: 1
tags: ["llm", "knowledge-cards", "moe", "performance"]
---

Active parameter 的核心概念是「[MoE](/llm/knowledge-cards/moe/) 模型每生成一個 token 實際參與 forward pass 的參數量」。跟模型總參數量是兩個獨立指標：**總參數**影響記憶體需求（要全部載入）、**active parameter** 影響推論速度上限（每 token 走的計算量）。Dense 模型的 active parameter 等於總參數；MoE 模型的 active parameter 通常只有總參數的 10% ~ 20%。

## 跟其他概念的關係

模型命名中的 active parameter 線索：

| 命名範例        | 解讀                                                          |
| --------------- | ------------------------------------------------------------- |
| `Qwen3-30B-A3B` | 30B 總參數、A3B 表示 active 約 3B                             |
| `Mixtral-8x7B`  | 8 個 7B expert、每 token top-2 啟用 ≈ 14B active（含 shared） |
| `Llama-3.3-70B` | Dense、active = total = 70B                                   |
| `DeepSeek-V3`   | 671B 總參數、active 約 37B（依官方文件）                      |

模型在不同維度的影響：

| 維度                     | 受影響因素                                                                                      |
| ------------------------ | ----------------------------------------------------------------------------------------------- |
| 記憶體需求               | 總參數 × 每權重 bytes                                                                           |
| 生字速度上限             | active parameter × 每 token 讀取量 / [memory bandwidth](/llm/knowledge-cards/memory-bandwidth/) |
| 模型能力（社群常見回報） | 較強相關於總參數、但 active parameter 是底線                                                    |

> **事實查核註**：active parameter 跟模型能力的關係是社群常見回報、不是嚴格定理；具體模型在 coding / reasoning / 對話等任務的表現依訓練資料、RLHF、prompt 風格變化、需以 [SWE-bench](/llm/knowledge-cards/swe-bench/) 等公開 benchmark 跟自己工作流校準。

## 判斷條件與後果

30B MoE 跟 30B Dense 在同一台硬體上生字速度差很多，原因是前者每個 token 只走約 3B active parameter，每個 token 要從記憶體讀的權重少了一個數量級。MoE 模型的能力也不等於同總參數的 Dense 模型：社群常見回報是接近總參數 60% ~ 80% 的 Dense 能力，而且依模型與任務而變。所以比較 MoE 與 Dense 時，三個量各自對應一個判斷：active parameter 對應生字速度上限，總參數對應記憶體需求，能力要靠自己工作流的 benchmark。把「30B」MoE 跟 Dense 30B 當成能力對等時，速度會低估、能力會高估。
