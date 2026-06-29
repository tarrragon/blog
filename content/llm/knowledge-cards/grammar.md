---
title: "Grammar"
date: 2026-05-14
description: "描述合法字串形狀的形式規則，在 structured output 中用來限制 LLM 每一步可輸出的 token"
weight: 1
tags: ["llm", "knowledge-cards", "structured-output", "grammar"]
---

Grammar（語法規則）的核心概念是「**用形式化規則描述哪些字串是合法輸出**」。在 LLM structured output 裡，grammar 是 parser / decoder 可以執行的規則集合，用來判斷 JSON、SQL、DSL、表達式或自訂格式是否符合預期形狀——此處的 grammar 指形式語法，而非英文文法。

## 概念位置

Grammar 位在格式定義層，常被 [constrained decoding](/llm/knowledge-cards/constrained-decoding/) 編譯成 token mask。它跟 schema 的差異在表達方式：schema 常描述資料結構與欄位限制，grammar 描述字串如何從符號規則生成；JSON Schema 適合物件欄位，grammar 適合自訂語言、查詢語法、括號結構與特定文字格式。

```text
grammar 規則 → parser / decoder 編譯
  ↓
每個生成位置算出合法 token
  ↓
不合法 token 被 mask 掉
```

## 可觀察訊號與例子

看到 `expr: term ("+" term)*`、`start: object`、`<json> ::= ...` 這類規則就是 grammar。例子是讓模型只輸出簡化查詢語言：欄位只能是 `status` / `owner`，運算子只能是 `=` / `in`，字串必須加引號；grammar 可以把非法查詢擋在生成階段。

Grammar 的邊界是語意與外部狀態。它可以限制語法合法，卻不能知道 `owner = "alice"` 是否真有這個使用者，也不能判斷查詢是否符合權限；這些仍要交給 validator、authorization 與業務規則。

## 設計責任

需要自訂輸出格式時，先判斷格式是資料結構還是小語言：物件欄位優先用 JSON Schema，小語言或查詢語法才用 grammar。下一步路由是：需要語法表示法讀 [BNF](/llm/knowledge-cards/bnf/) 或 [Lark Grammar](/llm/knowledge-cards/lark-grammar/)；需要應用層自訂語言讀 [DSL](/llm/knowledge-cards/dsl/)。
