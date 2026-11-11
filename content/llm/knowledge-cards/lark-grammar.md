---
title: "Lark Grammar"
date: 2026-05-14
description: "Lark parser 使用的 EBNF-like grammar 格式，常被 structured output 工具拿來描述自訂輸出語法"
weight: 1
tags: ["llm", "knowledge-cards", "grammar", "parser"]
---

Lark grammar 的核心概念是「**Lark parser 使用的一種 EBNF-like 語法描述格式**」。在 LLM structured output 文件中看到 lark grammar，通常是在說某個工具用 Lark 風格規則描述合法輸出，再把規則交給 parser 或 [constrained decoding](/llm/knowledge-cards/constrained-decoding/) engine。

## 跟其他概念的關係

Lark 是 Python 生態的 parsing toolkit，Lark grammar 是它的規則語言。它比傳統 [BNF](/llm/knowledge-cards/bnf/) 更接近實作格式，常見元素包含 rule、terminal、literal、repeat、optional、ignore whitespace 與 start rule。

```text
start: query
query: FIELD OP VALUE
FIELD: "status" | "owner"
OP: "=" | "!="
VALUE: ESCAPED_STRING
%import common.ESCAPED_STRING
%ignore " "
```

這段規則描述一個很小的查詢語言，只允許固定欄位、固定運算子與 quoted string。

## 可觀察訊號與例子

看到 `start:`、大寫 terminal、`%import common.*`、`%ignore`，通常就是 Lark grammar 或受它影響的格式。LLM 場景常用它描述 JSON 子集、SQL-like query、指令 DSL、分類輸出或固定格式報告。

Lark grammar 的風險是把 parser 格式誤當跨引擎標準。某些 constrained decoding 工具支援 Lark-like 語法，某些只支援 JSON Schema、regex、GBNF 或自家格式；搬規則前要確認目標 server 能不能解析同一套語法。

## 判斷條件與後果

Lark grammar 適用的條件有兩個：格式需要寫成清楚的自訂規則，而且目標工具鏈支援 Lark dialect；工具鏈只支援 JSON Schema、regex 或 GBNF 時，Lark 規則搬過去解析不了（上一段）。規則允許的範圍比應用需要的大時，模型可以生成應用處理不了的語法，所以合法範圍縮到應用實際需要的語法；語法合法之外的外部狀態與權限，grammar 判斷不了，由 validator 處理。延伸的概念在 [Grammar](/llm/knowledge-cards/grammar/) 與 [DSL](/llm/knowledge-cards/dsl/)。
