---
title: "Active Parameter"
date: 2026-05-12
description: "MoE 模型每生成一個 token 實際參與計算的參數量、跟模型總參數量不同、影響推論速度上限"
weight: 1
tags: ["llm", "knowledge-cards", "moe", "performance"]
---

Active parameter 的核心概念是「[MoE](/llm/knowledge-cards/moe/) 模型每生成一個 token 實際參與 forward pass 的參數量」。跟模型總參數量是兩個獨立指標：**總參數**影響記憶體需求（要全部載入）、**active parameter** 影響推論速度上限（每 token 走的計算量）。Dense 模型的 active parameter 等於總參數；MoE 模型的 active parameter 通常只有總參數的 10% ~ 20%。

## 概念位置

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

## 設計責任

理解 active parameter 後可以解釋兩個現象：為什麼 30B MoE 跟 30B Dense 在同硬體下生字速度差很多（前者每 token 只走 3B active）、為什麼 MoE 模型能力對應的「等價 Dense 大小」不是簡單線性（社群常見回報接近總參數的 60% ~ 80% 等價 Dense 能力、但 case-by-case）。

選 MoE 模型時、active parameter 是速度判讀軸、總參數是記憶體判讀軸、能力判讀靠自己工作流的 benchmark；不要直接拿「30B」跟 Dense 30B 作能力對等。
