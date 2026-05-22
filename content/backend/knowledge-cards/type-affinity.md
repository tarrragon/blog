---
title: "Type Affinity"
date: 2026-05-22
description: "說明 SQLite 如何用 type affinity 決定欄位的型別傾向與值的儲存方式"
weight: 350
---

Type Affinity 的核心概念是 SQLite 的型別模型 — 欄位宣告的型別不是硬約束，而是一個「傾向」，SQLite 依這個傾向決定存入的值如何被轉換與儲存。它讓 SQLite 的 schema 比嚴格型別資料庫更寬鬆，代價是要理解值實際被存成什麼。理解它對寫對 [Schema Migration](/backend/knowledge-cards/schema-migration/) 與查詢很關鍵。

## 概念位置

Type Affinity 位在 SQLite 的資料模型核心，和嚴格靜態型別的資料庫相對。多數關聯式資料庫的欄位型別是硬約束，存錯型別會被拒絕；SQLite 的欄位有 type affinity，值會被儘量依 affinity 轉換、也允許存入不同 storage class。它和 [Document Store](/backend/knowledge-cards/document-store/) 的彈性 schema 是不同來源的彈性 — 一個是型別寬鬆、一個是結構寬鬆。

## 可觀察訊號與例子

需要理解 type affinity 的訊號是查詢結果的型別或排序不如預期，或同一欄位混進了數字與字串。常見場景是把數字以字串存入，比較與排序就按字串規則跑；或預期欄位是整數、實際存進了文字。SQLite 的 STRICT table 可以把欄位改回硬約束，讓行為更接近傳統資料庫。

## 設計責任

設計 schema 時要清楚每個欄位的 type affinity、以及值會如何被轉換。需要嚴格型別保證時，要明確選用 STRICT table 或在應用層驗證。測試 fixture 要涵蓋型別邊界，避免「本機測試剛好都存對型別」掩蓋問題。
