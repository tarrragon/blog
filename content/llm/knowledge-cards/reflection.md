---
title: "Reflection / Self-critique"
date: 2026-05-14
description: "要求模型先輸出一版、再 critique 自己、再修改的 prompting / workflow 模式、有自身失敗模式"
weight: 1
tags: ["llm", "knowledge-cards", "prompting", "workflow"]
---

Reflection（self-critique）的核心概念是「**模型先生成一個草版、再對自己的草版 critique、再修改**」。屬於推理引導類的 prompting 技術、也是 [workflow pattern](/llm/04-applications/workflow-patterns/) 的基本模式之一。跟 [chain-of-thought](/llm/knowledge-cards/chain-of-thought/) 不同：CoT 是「過程要 explicit」、reflection 是「先寫一版再批評再改」、有明確的兩階段。

## 跟其他概念的關係

Reflection 三步：

```text
[Generate]    模型生成 v1
   ↓
[Critique]    模型（或 critic LLM）對 v1 給回饋
   ↓
[Refine]      模型按回饋生成 v2
   ↓
(可選 loop)
```

跟其他模式對照：

| 模式                                                     | 結構                               | 主要解的問題                 |
| -------------------------------------------------------- | ---------------------------------- | ---------------------------- |
| CoT                                                      | Think step by step、單次生成       | 隱式推理變 explicit          |
| Reflection                                               | Generate → critique → refine       | 一次生成不夠好、需要二次審視 |
| [Multi-step](/llm/knowledge-cards/multi-step-retrieval/) | Retrieve / decide / retrieve again | 資訊不足、要動態補資料       |

## 判斷條件與後果

Reflection 的修改只在 critique 找得到 generator 沒看到的錯誤時才有效，所以判斷看兩件事：critic 跟 generator 的盲點是否重疊，以及迴圈是否有客觀的停止點與比較基準。

1. **critic 跟 generator 是同一個模型時**，訓練分佈裡的盲點是共用的，「再想一次」不會讓它消失；訊號是 critique 每次給相似的建議，或修完仍是同一類錯。這類 systematic error 要靠一個不共用盲點的檢查者：換成不同 base model 的 critic，或用 test、lint、schema 這類外部驗證取代 LLM 的 critique。
2. **critic 的能力不足時**，它產不出有用的建議，reflection 只增加 cost 與 latency。
3. **沒有客觀的停止訊號時**，reflection 一直跑下去，cost 隨輪數持續增加；step cap 加上外部 metric（test pass、schema valid）給出停止點。
4. **每一輪的修改都直接採用時**，小改動逐輪累積成過度迎合 critic 意見的版本，最終結果可能比初稿差；保留初稿當 baseline，每一輪的結果跟 baseline 比過，沒有變好就不採用。

[Agent loop](/llm/knowledge-cards/agent-loop/) 是 reflection 的延伸特例、進階失敗模式見 [4.4 Agent 架構](/llm/04-applications/agent-architecture/)。完整 workflow pattern 比較見 [4.7 Workflow patterns](/llm/04-applications/workflow-patterns/)。
