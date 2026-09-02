---
title: "Semantic Model（語意模型）"
date: 2026-09-02
description: "文章說「模型定死」「符合語意模型」時，查那套規則是什麼、由誰保證"
weight: 18
tags: ["sql", "relational-algebra", "semantics", "knowledge-card"]
---

語意模型是「這段查詢的文字算出哪一份[關係](/sql/knowledge-cards/relation/)」這件事的規則。它只回答結果是什麼，不回答怎麼算到、要花多久。

規則的來源是[關聯代數](/sql/knowledge-cards/relational-algebra/)：每一個子句對應一個作用在[關係](/sql/knowledge-cards/relation/)上的運算，而查詢是那些運算的一個組合。代數是來源，語意模型是那套規則本身。

## 它與另外兩件事分開

**與執行方式分開。** [最佳化器](/sql/knowledge-cards/query-optimizer/)可以任意重排步驟，只受一個約束：輸出的關係要與語意模型算出來的一致。這個分工是「代價由資料與索引決定、不由寫法決定」的根據（[1.17](/sql/cost-lives-in-the-plan/)）。

**與書寫順序分開。** `SELECT` 寫在最前面而它在求值順序上排在後面，這正是語意模型與文字順序不同的地方（[1.2](/sql/clause-evaluation-order/)）。

## 它涵蓋的與它沒涵蓋的

模型定死的那些，換一家[引擎](/sql/knowledge-cards/database-engine/)不會變：三值邏輯讓條件的答案有第三種、外連接配不上時補 `NULL`、`NOT IN` 展開成一串連乘、分組把一組收成一列。這一批是本分類第一支的內容。

模型之外另有幾件事在決定同一段查詢的結果：識別字被摺成什麼樣、引擎接不接受標準禁止的寫法並自己補一個值、送出這段 SQL 的人被允許讀哪些表。這一批是第二支的內容，而它們與模型的差別是——模型的規則各家一致，這幾項不一致。

## 概念位置

**「符合語意模型」與「答案對了」是兩件事。** 模型與[約束](/sql/knowledge-cards/constraint/)的分工也在這條線上——約束管資料能長成什麼樣，模型管那批資料算出什麼。 模型保證的是這段文字算出哪一批列，而那批列是不是要問的那個問題的答案，模型不管也管不到——問題不在查詢裡（[1.13](/sql/well-formed-is-not-correct/)）。第一支反覆出現的那幾類安靜的錯誤，全部發生在模型算對了的前提下。

## 往下走

規則的來源與封閉性在 [Relational Algebra（關聯代數）](/sql/knowledge-cards/relational-algebra/)。模型與書寫順序、執行順序怎麼分開，在 [1.1 宣告式的紅利與代價](/sql/declarative-not-procedural/)。模型之外那幾方各決定什麼，在 [Database Engine（資料庫引擎）](/sql/knowledge-cards/database-engine/)。
