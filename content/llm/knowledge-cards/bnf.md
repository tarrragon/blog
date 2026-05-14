---
title: "BNF（Backus-Naur Form）"
date: 2026-05-14
description: "用遞迴產生式描述語法的經典記法，是 CFG、parser 與 grammar-constrained sampling 常見的基礎表示"
weight: 1
tags: ["llm", "knowledge-cards", "grammar", "parser"]
---

BNF（Backus-Naur Form）的核心概念是「**用產生式規則描述一個語言裡哪些字串合法**」。它常用在程式語言、資料格式、parser 與 structured output grammar，讓人跟工具都能用同一份規則理解合法語法。

## 概念位置

BNF 是 [grammar](/llm/knowledge-cards/grammar/) 的一種表示法，特別適合描述 context-free grammar。規則左邊是非終結符，右邊是它可以展開成的符號組合；終結符是實際會出現在字串中的 token，非終結符是中間抽象節點。

```text
<expr> ::= <term> | <expr> "+" <term>
<term> ::= <number> | "(" <expr> ")"
```

這段規則表示 expression 可以是 term，也可以是 expression 加 term；term 可以是 number，也可以是括號包住的 expression。

## 可觀察訊號與例子

看到 `::=`、`<name>`、多個展開選項，就是 BNF 或 BNF-like grammar。LLM structured output 文章裡提到 BNF，通常是在說「把合法輸出格式寫成形式語法，推論時用它限制生成」。llama.cpp 的 GBNF、部分 grammar engine 與 parser 文件都會使用類似記法。

BNF 的限制是它描述語法，不描述語意。它能表示「括號必須成對」「欄位順序合法」，但不能直接表示「日期必須晚於今天」「使用者必須有權限讀這筆資料」這類外部約束。

## 設計責任

BNF 適合拿來讀懂 grammar-constrained sampling 的規則形狀。實作時要確認你使用的引擎支援的是標準 BNF、EBNF、GBNF，還是自家 dialect；不同 dialect 的 optional、repeat、token escaping 寫法會不同。下一步路由是 [Grammar](/llm/knowledge-cards/grammar/) 與 [Lark Grammar](/llm/knowledge-cards/lark-grammar/)。
