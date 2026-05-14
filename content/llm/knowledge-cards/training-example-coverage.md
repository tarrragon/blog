---
title: "Training Example Coverage"
date: 2026-05-14
description: "訓練資料中的任務範例是否覆蓋足夠情境，決定模型在 function calling、格式輸出與邊界案例上的穩定性"
weight: 1
tags: ["llm", "knowledge-cards", "training", "evaluation"]
---

Training example coverage（訓練範例覆蓋度）的核心概念是「**模型在訓練時看過的任務情境是否足以支撐部署時遇到的變化**」。LLM 的能力宣稱常寫成支援某功能，但實際穩定性取決於範例是否覆蓋工具數量、參數形狀、語言變體、錯誤情境與 edge cases。

## 概念位置

Coverage 是訓練資料分佈的問題，常在 [SFT](/llm/knowledge-cards/sft/)、偏好資料、tool-use data、domain fine-tune 裡出現。它跟 prompt 範例不同：few-shot 範例只存在於當次 context，training examples 會透過訓練更新模型權重，影響模型「自然」傾向怎麼回答。

```text
訓練資料有覆蓋 → 模型自然輸出穩定
訓練資料缺口大 → 靠 prompt / structured output / validator 兜底
```

## 可觀察訊號與例子

Function calling 的 coverage 可從四個面向判讀：該呼叫時是否呼叫、工具選擇是否正確、參數型別是否正確、巢狀 schema 與多工具情境是否穩定。小模型常在單一工具 + 平坦 schema 表現可用，但一進到多工具、optional field、nested object、跨語言 query 就明顯掉分，這通常是 coverage 不足而不是單純 parser 問題。

Coverage 的陷阱是只看 happy path。訓練範例如果只有成功呼叫工具，模型會傾向每次都呼叫；如果缺少「資訊不足時先追問」「使用者要求超出權限時拒絕」「工具錯誤時重試或回退」這類範例，部署後會在安全與可靠性邊界失敗。

## 設計責任

評估模型能力時，把支援功能改問成覆蓋範圍：支援哪些 tool schema 複雜度、哪些語言、哪些錯誤路徑、哪些反例。下一步路由是用 eval set 補齊代表性情境；如果 coverage 無法補在模型訓練層，就用 [structured output](/llm/knowledge-cards/structured-output/)、validator、retry 與 fallback 降低失敗成本。
