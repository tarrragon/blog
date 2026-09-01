---
title: "ORM（Object-Relational Mapping）"
date: 2026-09-01
description: "看到程式用類別與方法描述查詢時，查它交出去的是什麼、以及哪些行為在程式碼上讀不出來"
weight: 442
tags: ["backend", "orm", "persistence", "database", "knowledge-card"]
---

ORM 把資料表對映成程式語言的類別，把一列對映成一個物件。寫的時候操作的是物件與方法，而它在送出之前把那串方法翻成一段 SQL 交給資料庫執行——**它是查詢的產生器，不是運算的執行者**。Python 的 SQLAlchemy 與 Django ORM、Ruby 的 ActiveRecord、Java 的 Hibernate 都屬於這一類，而它們送出的每一段查詢都經過同一個 [connection pool](/backend/knowledge-cards/connection-pool/)。

## 它買到什麼

**型別與工具**：欄位變成類別的屬性，編輯器補得出來、型別檢查看得到，而字串拼出來的 SQL 兩者都沒有。

**組合性**：篩選條件可以分段加上去再一次送出，不必自己拼字串。

**跨引擎的方言差異**：同一段程式碼在不同資料庫上產生的 SQL 不同，由 ORM 吸收。

## 它讓什麼變得看不見

程式碼與實際送出的 SQL 之間隔了一層，所以**這一段會打幾次資料庫**在程式碼上讀不出來。兩種常見的形態：

- **延遲載入**：存取一個關聯屬性才去查一次，寫在迴圈裡就變成一次請求打上百次查詢，也就是 N+1
- **交易邊界不明**：一段程式碼是不是在同一個交易裡，由框架的設定與作用域決定而不由這幾行決定（見 [transaction boundary](/backend/knowledge-cards/transaction-boundary/)）

處置的方向一致：讓實際送出的 SQL 現形。多數 ORM 有印出查詢的開關，開發時開著。

## 概念位置

ORM 站在應用程式與資料庫之間，運算仍然發生在資料庫那一端——它交出去的是描述，回來的是結果。這一點決定了它的容量上限跟著資料庫走，與把整批資料搬進記憶體再算的工具（[DataFrame](/sql/knowledge-cards/dataframe/) 那一類）分屬兩側。

連線這一層同樣被它蓋住：每一段查詢佔用的仍然是 [connection pool](/backend/knowledge-cards/connection-pool/) 裡的一條連線，而是哪一條、佔多久由框架的作用域與連線池的設定決定。

它也不是查詢語言的替代品。複雜的分析查詢用 ORM 表達得很吃力，多數專案在那些地方直接寫 SQL。

## 往下走

它與 DataFrame 各自產出什麼、以及外觀相似的方法串接底下差了什麼，在 [python 模組八 8.3](/python/08-data-analysis/orm-and-dataframe/)。延遲載入與長交易的可診斷清單、以及每請求的查詢次數預算，在 [查詢反模式](/backend/01-database/query-anti-patterns/)。
