---
title: "DataFrame（資料框）"
date: 2026-09-01
description: "SQL 教材拿 pandas 或資料框當對照時，查 DataFrame 是什麼、它與資料表差在哪"
weight: 12
tags: ["sql", "dataframe", "pandas", "declarative", "knowledge-card"]
---

DataFrame 是一張表在程式記憶體裡的表示：有具名的欄、有列，整份資料握在執行這段程式的行程手上。Python 的 pandas 是最常見的實作，R 與 Julia 各有自己的一套。它與 [relation](/sql/knowledge-cards/relation/)——一組欄位固定、由若干列構成的資料集合，資料表是它的一種——裝的內容幾乎一樣，而兩者在三個地方分開。

## 三個分開的地方

**列有沒有順序。** DataFrame 的列從頭到尾有一個位置，可以問「第三列是什麼」。關係沒有順序這個屬性，`SELECT` 回來的列要靠 `ORDER BY` 才排得出來。

**誰在算。** 對 DataFrame 的每一個操作在自己的行程裡執行，資料先整批進記憶體；對關係的操作交給資料庫引擎，程式收到的只有結果。上限因此不同——一邊是這台機器的記憶體，一邊是資料庫的儲存。

**寫下的是動作還是描述。** DataFrame 的程式碼是一串照順序發生的動作：載入、篩選、合併。SQL 寫下的是要什麼結果，怎麼算由引擎決定。這一條是 [SQL 這個分類](/sql/)每一篇的起點。

## 概念位置

DataFrame 在 SQL 那個分類裡的角色是對照組。宣告式這個性質單獨看不出形狀，跟一段逐步執行的程式並排才清楚——同一件事，一邊每一行指定下一步做什麼，一邊只描述要什麼。

兩邊的底層是同一套 [關聯代數](/sql/knowledge-cards/relational-algebra/)，所以多數操作對得上；對不上的地方正好落在上面那三項差別上。

## 往下走

宣告式與逐步執行的完整對照、以及三種順序的分工，在 [1.1 宣告式的紅利與代價](/sql/declarative-not-procedural/)。同一組操作在兩種介面上的四組對應與對應斷掉的三個位置，在 [python 模組八 8.4](/python/08-data-analysis/same-relational-algebra/)。
