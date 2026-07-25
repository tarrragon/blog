---
title: "Capability Spectrum"
date: 2026-05-14
description: "把模型能力視為連續光譜而非支援 / 不支援二分，用覆蓋度、穩定性與失敗模式判讀真實可用性"
weight: 1
tags: ["llm", "knowledge-cards", "evaluation"]
---

Capability spectrum（能力光譜）的核心概念是「**LLM 能力通常是連續程度，不是支援 / 不支援的二元開關**」。同樣宣稱支援 [function calling](/llm/knowledge-cards/function-calling/)、reasoning、coding、structured output 的模型，可能在簡單案例都成功，但在長 context、多工具、巢狀 schema、模糊需求或反例情境下出現巨大差距。

## 概念位置

能力光譜是評估與選型用語，用來替代 binary checklist（相關概念見 [jagged frontier](/llm/knowledge-cards/jagged-frontier/)）。它把能力拆成範圍、穩定性、成本與失敗模式：模型能做什麼、在多寬的分佈上穩定、錯的時候怎麼錯、需要多少 prompt / validator / retry 才可用。

```text
宣稱支援 → happy path 可用
基礎可用 → 常見變體可用
生產可用 → edge cases、錯誤路徑、壓力情境仍可控
```

## 可觀察訊號與例子

Function calling 的能力光譜可以用幾個訊號量化：單工具成功率、多工具選擇成功率、schema 合法率、參數語意正確率、錯誤時是否追問。某模型能輸出合法 JSON，不代表它能選對工具；能選對工具，也不代表它能填對 nested argument。

能力光譜的常見陷阱是把 demo 成功當成生產穩定。Demo 通常測 happy path，生產會遇到拼字錯、缺欄位、權限不足、工具 timeout、prompt injection、schema 演化與多語言輸入；這些才決定能力落在哪個位置。

## 設計責任

做模型選型或應用設計時，把「有沒有」改成「到什麼程度可用」。判準要包含成功率、覆蓋範圍、錯誤成本、監控訊號與回退路徑。下一步路由是：能力來自訓練資料時讀 [Training Example Coverage](/llm/knowledge-cards/training-example-coverage/)；能力需要推論階段兜底時讀 [Sampling Constraint](/llm/knowledge-cards/sampling-constraint/)。
