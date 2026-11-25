---
title: "DataFrame（資料框）"
date: 2026-09-01
description: "SQL 文章以 pandas 或資料框作為對照組時，查閱 DataFrame 與資料表及關係的差別"
aliases: ["/sql/knowledge-cards/dataframe/"]
weight: 12
tags: ["sql", "dataframe", "pandas", "declarative", "knowledge-card"]
---

把二維表格資料放進應用程式記憶體中操作時，常見的資料結構稱為 DataFrame（資料框），具備具名欄位與列集合，典型實作包含 Python 的 pandas 以及 R 與 Julia 的資料框。它與資料庫裡的 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/)（欄位固定、由若干列構成的資料集合）承載相似的表格內容，但在列序、執行位置與表達風格三個面向不同。

## 與關係的差異：列序、執行位置與表達風格

- **列序**：DataFrame 的列具備明確位置索引，可直接存取「第三列」；關係屬於無序集合，必須透過 `ORDER BY` 才會產生固定順序。
- **執行位置與容量上限**：DataFrame 的運算在應用程式自身行程的記憶體中執行，容量受限於單機記憶體；SQL 操作交由資料庫引擎在資料庫端執行，應用程式只接收最終結果，容量上限取決於資料庫儲存與引擎配置。
- **命令式與宣告式**：DataFrame 程式碼逐步指定載入、篩選、合併等操作步驟；SQL 僅描述想要的結果集合，執行演算法交由最佳化器決定。

## 跟其他概念的關係

DataFrame 在 SQL 教學中作為命令式對照組，用來突顯宣告式語言把「描述結果」與「執行步驟」分離的性質。

由於兩者的底層操作皆源自 [Relational Algebra（關聯代數）](/backend/01-database/sql/knowledge-cards/relational-algebra/)，選取、投影、連接與分組在兩種介面多數能一一對應，無法對應之處正是列序、空值與索引這幾項差異。

## 延伸閱讀：宣告式特性與 pandas 對照

- 宣告式語言的三種順序分工：[SQL.1 宣告式的紅利與代價：書寫、求值與執行順序各自由誰決定](/backend/01-database/sql/declarative-not-procedural/)
- SQL 子句與 pandas 方法的逐項對照與差異：[8.4 SQL 子句與 pandas 方法的對應：篩選、連接、分組彙總、視窗函數，以及空值、索引與順序的語意差異](/programming/python/basic/08-data-analysis/same-relational-algebra/)
