---
title: "Training Example Coverage"
date: 2026-05-14
description: "訓練資料中的任務範例是否覆蓋足夠情境，決定模型在 function calling、格式輸出與邊界案例上的穩定性"
weight: 1
tags: ["llm", "knowledge-cards", "training", "evaluation"]
---

Training example coverage（訓練範例覆蓋度）的核心概念是「**模型在訓練時看過的任務情境是否足以支撐部署時遇到的變化**」。LLM 的能力宣稱常寫成支援某功能（例如 [function calling](/llm/knowledge-cards/function-calling/)），但實際穩定性取決於範例是否覆蓋工具數量、參數形狀、語言變體、錯誤情境與 edge cases。

## 跟其他概念的關係

Coverage 是訓練資料分佈的問題，常在 [SFT](/llm/knowledge-cards/sft/)、偏好資料、tool-use data、domain fine-tune 裡出現。它跟 prompt 範例不同：few-shot 範例只存在於當次 context，training examples 會透過訓練更新模型權重，影響模型「自然」傾向怎麼回答。

```text
訓練資料有覆蓋 → 模型自然輸出穩定
訓練資料缺口大 → 靠 prompt / structured output / validator 兜底
```

## 可觀察訊號與例子

Function calling 的 coverage 可從四個面向判讀：該呼叫時是否呼叫、工具選擇是否正確、參數型別是否正確、巢狀 schema 與多工具情境是否穩定。小模型常在單一工具 + 平坦 schema 表現可用，但一進到多工具、optional field、nested object、跨語言 query 就明顯掉分，這通常是 coverage 不足而不是單純 parser 問題。

Coverage 的陷阱是只看 happy path。訓練範例如果只有成功呼叫工具，模型會傾向每次都呼叫；如果缺少「資訊不足時先追問」「使用者要求超出權限時拒絕」「工具錯誤時重試或回退」這類範例，部署後會在安全與可靠性邊界失敗。

## 判斷條件與後果

模型宣稱支援某個功能時，部署後穩不穩定取決於訓練範例覆蓋到哪裡：tool schema 的複雜度、語言、錯誤路徑與反例。部署遇到的情境在覆蓋範圍內時，模型的輸出自然穩定；超出範圍時（多工具、nested object、跨語言 query、工具出錯之後的處理），模型照訓練時的傾向回答，例如每次都呼叫工具，在安全與可靠性的邊界上失敗。「支援」兩個字不帶出範圍，所以範圍要靠一份列進代表性情境的 eval set 量出來，掉分的情境就是 coverage 的缺口。缺口補不進模型訓練層時，模型在那些情境的輸出仍然不穩，失敗的成本改由執行層的 [structured output](/llm/knowledge-cards/structured-output/)、validator、retry 與 fallback 攔下與降低。
