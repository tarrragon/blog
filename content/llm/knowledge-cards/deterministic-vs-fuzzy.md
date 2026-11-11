---
title: "Deterministic vs Fuzzy engineering"
date: 2026-05-14
description: "LLM 軟體 vs 傳統軟體在資料 / 邏輯 / 行為一致性 / 實驗成本四維度的典範差異、決定哪段該包 guardrail"
weight: 1
tags: ["llm", "knowledge-cards", "paradigm", "architecture"]
---

Deterministic vs Fuzzy engineering 的核心概念是「**LLM 軟體跟傳統軟體在設計典範上的根本差異**」。Deterministic 軟體建立在「同 input → 同 output」假設、fuzzy 軟體建立在「同 input → 分佈」假設。兩者在資料、邏輯、行為一致性、實驗成本四維度都不同、設計直覺要分開。實務上一個 LLM 應用是兩者混合、[guardrail](/llm/knowledge-cards/guardrail/) 設計是把 fuzzy 邊界包進 deterministic 約束。

## 跟其他概念的關係

四維對照：

| 維度       | Deterministic 軟體     | Fuzzy 軟體                         |
| ---------- | ---------------------- | ---------------------------------- |
| 資料形狀   | 結構化（JSON、DB row） | 半結構化 / 非結構化                |
| 邏輯來源   | 人類寫死規則           | 模型推論、依 prompt + context 浮動 |
| 行為一致性 | 同 input → 同 output   | 同 input → 分佈                    |
| 分解原則   | 按職責 / 模組          | 按角色 / agent                     |
| 測試方式   | unit test、覆蓋率      | eval、judge、distribution metric   |
| 實驗成本   | 高                     | 低（改 prompt 即可）               |

典型 [agent](/llm/knowledge-cards/agent/) 應用的混合：

```text
User input
   ↓ Fuzzy（LLM 理解意圖）
   ↓ Deterministic（DB / API / policy）
   ↓ Fuzzy（LLM 寫回應）
   ↓ Deterministic（發送 / 寫入）
```

## 判斷條件與後果

讀 LLM 應用設計文章或開始設計 production AI 系統時、這個 framing 決定每個 step 的工具選擇。實作判讀：

1. **這一步的規則可窮舉、失敗代價高、需要解釋或需要 byte-exact 重現時**：這一步屬於 deterministic，因為模型的輸出是分佈，同一個輸入可能得到不同結果，給不出重現與解釋。輸入是自由文字、輸出要有風格、邊界模糊時屬於 fuzzy，因為規則寫不完這些情形。
2. **典範用反時**：deterministic 需求交給 LLM（用 LLM 算稅金），得到的是偶爾出錯而無法重現的結果；fuzzy 需求寫成規則（regex 解析自由文字），在規則沒涵蓋的輸入上失效；兩邊混在同一處（prompt 裡做算術、code 裡做意圖分類）時，出錯了分不出是哪一側的責任。
3. **fuzzy 的輸出交給 deterministic 的步驟時**：邊界上有四種 guardrail，schema validation、output validator、action gating、distribution monitoring，各自攔不同 risk class 的錯誤，通常混合使用。[HITL](/llm/knowledge-cards/human-in-the-loop/) 也是一種 deterministic guardrail：把人類判斷當成檢查點，包住 LLM 的行為。
4. **系統出錯時**：deterministic 軟體的錯誤歸因到單一的程式碼路徑；fuzzy 系統的錯誤可能來自 prompt、model、context、tool 或 deterministic glue code，要逐層區分才找得到原因。

完整典範討論見 [0.8 Deterministic vs Fuzzy Engineering](/llm/00-foundations/deterministic-vs-fuzzy-engineering/)。
