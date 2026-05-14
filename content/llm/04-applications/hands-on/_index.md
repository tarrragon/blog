---
title: "4.x Hands-on：端到端案例"
date: 2026-05-14
description: "把模組四的所有原理串成具體 case study：從 task decomposition、workflow 設計、eval 設計到 iteration loop"
tags: ["llm", "applications", "hands-on", "case-study"]
weight: 99
---

本子資料夾收錄把模組四原理串起來的端到端案例。跟前面 principle-first 章節的差別：principle 章節是「跨工具不變的原理」、hands-on 是「把這些原理放在同一個任務上、走一遍完整流程」。

讀法建議：先讀 principle 章節建立心智模型、再進 hands-on 看「實際做的時候、原理怎麼落」。

## 案例列表

| 案例                                                                                             | 主題                                               | 對應原理章節                                                                                   |
| ------------------------------------------------------------------------------------------------ | -------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| [Customer support agent 從零到 eval](/llm/04-applications/hands-on/customer-support-case-study/) | Task decomposition → 設計 → trace → eval → iterate | 4.0 prompt / 4.1 RAG / 4.3 tool / 4.4 agent / 4.5 HITL / 4.7 workflow / 4.13 eval / 4.20 trace |
