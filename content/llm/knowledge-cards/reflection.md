---
title: "Reflection / Self-critique"
date: 2026-05-14
description: "要求模型先輸出一版、再 critique 自己、再修改的 prompting / workflow 模式、有自身失敗模式"
weight: 1
tags: ["llm", "knowledge-cards", "prompting", "workflow"]
---

Reflection（self-critique）的核心概念是「**模型先生成一個草版、再對自己的草版 critique、再修改**」。屬於推理引導類的 prompting 技術、也是 [workflow pattern](/llm/04-applications/workflow-patterns/) 的基本模式之一。跟 [chain-of-thought](/llm/knowledge-cards/chain-of-thought/) 不同：CoT 是「過程要 explicit」、reflection 是「先寫一版再批評再改」、有明確的兩階段。

## 概念位置

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

## 設計責任

讀 prompt engineering / agent paper 看到「reflection」「self-critique」「self-refine」「critic」就是這個機制。實作判讀：

1. **適用模型有能力辨識「自己寫的不夠好」**、critique 跟 generator 不會共用同樣 blind spot。
2. **失敗在 systematic error**：critique 跟 generator 是同個模型、訓練分佈中的盲點不會因為「再想一次」消失。判讀訊號：critique 每次給很像的建議、或修完還是同一類錯——換 critic 用不同 base model、或加外部驗證（test、lint、schema）取代 LLM critique。
3. **失敗在低能力模型**：critic 能力不足、產不出有用建議、徒增 cost / latency。
4. **失敗在無限循環**：沒有客觀停止訊號、reflection 一直跑、cost 爆掉。緩解：step cap + 外部 metric（test pass、schema valid）。
5. **失敗在過度修正**：每次 reflection 都改一點、累積結果變糟（過度 fitting critic 意見）。緩解：保留 baseline、reflection 結果要跟 baseline 比、不一定採用。

[Agent loop](/llm/knowledge-cards/agent-loop/) 是 reflection 的延伸特例、進階失敗模式見 [4.4 Agent 架構](/llm/04-applications/agent-architecture/)。完整 workflow pattern 比較見 [4.7 Workflow patterns](/llm/04-applications/workflow-patterns/)。
