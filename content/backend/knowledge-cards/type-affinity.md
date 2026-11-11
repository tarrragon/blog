---
title: "Type Affinity"
date: 2026-05-22
description: "說明 SQLite 如何用 type affinity 決定欄位的型別傾向與值的儲存方式"
weight: 351
---

Type Affinity 的核心概念是 SQLite 的型別模型 — 欄位宣告的型別是一個「傾向」，SQLite 依這個傾向決定存入的值如何被轉換與儲存，硬約束的心智模型在此不適用。它讓 SQLite 的 schema 比嚴格型別資料庫更寬鬆，代價是要理解值實際被存成什麼。理解它對寫對 [Schema Migration](/backend/knowledge-cards/schema-migration/) 與查詢很關鍵。

## 跟其他概念的關係

Type Affinity 位在 SQLite 的資料模型核心，和嚴格靜態型別的資料庫相對。多數關聯式資料庫的欄位型別是硬約束，存錯型別會被拒絕；SQLite 的欄位有 type affinity，值會被儘量依 affinity 轉換、也允許存入不同 storage class。它和 [Document Store](/backend/knowledge-cards/document-store/) 的彈性 schema 是不同來源的彈性 — 一個是型別寬鬆、一個是結構寬鬆。

## 可觀察訊號與例子

需要理解 type affinity 的訊號是查詢結果的型別或排序不如預期，或同一欄位混進了數字與字串。常見場景是把數字以字串存入，比較與排序就按字串規則跑；或預期欄位是整數、實際存進了文字。SQLite 的 STRICT table 可以把欄位改回硬約束，讓行為更接近傳統資料庫。

## 判斷條件與後果

欄位的 type affinity 決定存進去的值實際成為哪一種 storage class。值被存成與預期不同的類型時（數字以字串存入），比較與排序照字串規則進行，查詢結果與預期不符而 SQLite 不報錯，原因是 affinity 只是傾向，不拒絕寫入。應用需要型別保證時有兩個位置可以擋：STRICT table 讓 SQLite 拒絕型別不符的值，應用層驗證在寫入前擋下。測試 fixture 只放型別正確的值時，混型別的情形要到 production 才出現，所以 fixture 裡放進型別邊界的值。
