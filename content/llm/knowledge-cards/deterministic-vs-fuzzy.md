---
title: "Deterministic vs Fuzzy engineering"
date: 2026-05-14
description: "LLM 軟體 vs 傳統軟體在資料 / 邏輯 / 行為一致性 / 實驗成本四維度的典範差異、決定哪段該包 guardrail"
weight: 1
tags: ["llm", "knowledge-cards", "paradigm", "architecture"]
---

Deterministic vs Fuzzy engineering 的核心概念是「**LLM 軟體跟傳統軟體在設計典範上的根本差異**」。Deterministic 軟體建立在「同 input → 同 output」假設、fuzzy 軟體建立在「同 input → 分佈」假設。兩者在資料、邏輯、行為一致性、實驗成本四維度都不同、設計直覺要分開。實務上一個 LLM 應用是兩者混合、guardrail 設計是把 fuzzy 邊界包進 deterministic 約束。

## 概念位置

四維對照：

| 維度        | Deterministic 軟體                | Fuzzy 軟體                           |
| ----------- | --------------------------------- | ------------------------------------ |
| 資料形狀    | 結構化（JSON、DB row）            | 半結構化 / 非結構化                  |
| 邏輯來源    | 人類寫死規則                      | 模型推論、依 prompt + context 浮動   |
| 行為一致性  | 同 input → 同 output              | 同 input → 分佈                      |
| 分解原則    | 按職責 / 模組                     | 按角色 / agent                       |
| 測試方式    | unit test、覆蓋率                 | eval、judge、distribution metric     |
| 實驗成本    | 高                                | 低（改 prompt 即可）                 |

典型 LLM 應用的混合：

```text
User input
   ↓ Fuzzy（LLM 理解意圖）
   ↓ Deterministic（DB / API / policy）
   ↓ Fuzzy（LLM 寫回應）
   ↓ Deterministic（發送 / 寫入）
```

## 設計責任

讀 LLM 應用設計文章或開始設計 production AI 系統時、這個 framing 決定每個 step 的工具選擇。實作判讀：

1. **哪段該 deterministic / 哪段該 fuzzy**：規則可窮舉、失敗代價高、需要解釋、需要 byte-exact 重現的 → deterministic；自由文字輸入、生成有風格的輸出、邊界模糊的 → fuzzy。
2. **典範用錯的反模式**：deterministic 需求硬用 fuzzy（用 LLM 算稅金）、fuzzy 需求硬用 deterministic（regex 解析自由文字）、邊界混（prompt 內塞算術 / code 內塞意圖分類）。
3. **Fuzzy 邊界的四種 guardrail**：schema validation、output validator、action gating、distribution monitoring。混用、不同 risk class 分擔不同層。
4. **跟 [HITL](/llm/knowledge-cards/human-in-the-loop/) 的關係**：HITL 是 deterministic guardrail 的一種——把人類判斷當 deterministic check 包 fuzzy LLM 行為。
5. **失敗的歸因分層**：壞掉時要問「是 prompt / model / context / tool / 還是 deterministic glue 的 bug」。deterministic 軟體歸因單一、fuzzy 軟體要分這幾層查。

完整典範討論見 [0.8 Deterministic vs Fuzzy Engineering](/llm/00-foundations/deterministic-vs-fuzzy-engineering/)。
