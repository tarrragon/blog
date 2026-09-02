---
title: "Database Engine（資料庫引擎）"
date: 2026-09-02
description: "文章說「引擎決定」「換一家引擎就不同」時，查那是哪一個層次的決定"
weight: 17
tags: ["sql", "engine", "portability", "knowledge-card"]
---

資料庫引擎是收下查詢的文字、按自己的規則算出結果並交回一份[關係](/sql/knowledge-cards/relation/)的那個軟體。SQLite、PostgreSQL、MySQL、DuckDB 各是一個引擎，而同一個引擎的不同版本也可能有不同的規則。

本分類反覆說「引擎」在做某件事，說的都是同一件事——差別在它做的是哪一種決定，而那決定了換一家引擎會不會得到不同的結果。

## 它的四種決定，換引擎的後果各不相同

**接不接受這段文字。** 引擎檢查名字解析得到、型別配得上、子句的組合合乎規則。標準定死的那些各家一致；標準禁止而各家自行放寬的那些不一致，於是同一段查詢在一家報錯、在另一家跑得動（[1.2](/sql/clause-evaluation-order/) 與 [1.9](/sql/grouping-key-decides-the-unit/) 各有一個實例）。

**名字指向哪個物件。** 沒加引號的識別字被摺成什麼樣由引擎決定，各家的規則不同（[1.14](/sql/identifier-rules/)）。

**要花多久。** 這由[最佳化器](/sql/knowledge-cards/query-optimizer/)決定，而它受一個約束：輸出的列集合要與語意模型算出來的一致。所以換引擎會換掉代價，不換掉答案（[1.17](/sql/cost-lives-in-the-plan/)）。

**回哪一批列。** 這一項由[關聯代數](/sql/knowledge-cards/relational-algebra/)的組合規則定死，各家一致。三值邏輯、外連接補 `NULL`、`NOT IN` 的展開方式都在這一層，所以那幾類錯誤換引擎不會消失（[1.6](/sql/join-changes-rows-and-nulls/)）。

## 概念位置

**引擎是「文字之外」那幾方裡射程最大的一方**——識別字規則、寬鬆度與設定、[最佳化器](/sql/knowledge-cards/query-optimizer/)都住在它裡面，而權限系統是它另外管的一層（[1.16](/sql/privilege-model/)）。所以「換一家引擎」這句話涵蓋的變動比它聽起來的多。

引擎不決定的只有一件事：這批列是不是那個問題的答案。那一層沒有機械判定，理由在 [1.13](/sql/well-formed-is-not-correct/)。

錯誤訊息的措辭由引擎決定而且會隨版本改，所以各篇引的那些字串是對照用的——判讀看它拒絕了什麼，不看它怎麼說。

## 往下走

各家在同一段查詢上的分歧最集中的地方，在 [1.14 識別字送進引擎之後會被改寫](/sql/identifier-rules/)。挑執行方式的那個元件在 [Query Optimizer（查詢最佳化器）](/sql/knowledge-cards/query-optimizer/)，它產出的那份計畫在 [Query Plan（執行計畫）](/sql/knowledge-cards/query-plan/)。它另外存著的那份摘要在 [Query Statistics（統計資訊）](/sql/knowledge-cards/query-statistics/)。
