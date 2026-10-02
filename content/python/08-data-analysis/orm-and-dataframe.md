---
title: "8.3 ORM 與 DataFrame 的分辨：回傳值的形狀、連線物件與查詢送出的時機"
date: 2026-08-31
description: "ORM 產生查詢、DataFrame 執行運算，以及外觀相似的方法串接底下差了什麼"
weight: 3
tags: ["python", "pandas", "orm", "sqlalchemy", "dataframe"]
---

[ORM](/backend/knowledge-cards/orm/) 的產出是一段 SQL 與一組物件，DataFrame 的產出是一張新的表格。兩者的寫法看起來相似，因為都用方法串接描述篩選條件，而底下發生的事完全不同：ORM 是查詢的產生器，DataFrame 是運算的執行者。

## ORM 的產出與運算發生的位置

ORM 把資料表對應成類別、把資料列對應成物件。篩選條件寫成屬性的比較式，框架把它翻譯成 SQL 的 `WHERE` 子句。

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

stmt = select(Customer).where(Customer.age > 18)
print(stmt.compile(engine))
# SELECT customer.id, customer.name, customer.age FROM customer WHERE customer.age > ?

with Session(engine) as s:
    rows = s.scalars(stmt).all()
    print([type(r).__name__ for r in rows], [r.name for r in rows])
    # ['Customer'] ['A']
```

`stmt` 本身還沒有做任何運算，它是一段待送出的查詢。運算在資料庫那一端完成，回來的每一列被包成一個 `Customer` 實例——所以拿到的是物件，可以呼叫它的方法、走訪它關聯到的其他物件。

## DataFrame 的產出與運算發生的位置

pandas 這一側的同一件事：

```python
df = pd.DataFrame({"id": [1, 2], "name": ["A", "B"], "age": [20, 10]})
df[df["age"] > 18]
#    id name  age
# 0   1    A   20
```

`df["age"] > 18` 先算出一個布林陣列 `[True, False]`，外層的取值用這個陣列挑出要留下的列。整段運算發生在這個程序的記憶體裡，沒有連線、沒有 SQL、沒有另一個系統參與。

回來的是一張新的表格，不是一組物件。它可以繼續被篩選、被合併、被彙總，因為表格正是這些操作接受的輸入。

## 分辨 ORM 與 DataFrame 的訊號：回傳值的形狀、連線物件、查詢送出的時機

外觀相似的方法串接底下，有三個分得開的訊號。

**回傳值的形狀。** 一組各自獨立、可以呼叫方法的實例，是 ORM 那一側；一張有欄有列、可以繼續被篩選與彙總的表格，是 DataFrame 那一側。

**有沒有連線物件。** 資料庫端的工具一定要先有一個連線或 session，因為運算要送去別的地方。pandas 的操作不需要：資料一旦載進 DataFrame，之後每一步都在這份記憶體裡的副本上進行，原本那個資料庫或檔案後來有沒有變動都不影響它。

**查詢送出的時機。** ORM 允許先把查詢組好、之後才送出，所以「描述」與「執行」是兩個時刻。pandas 的每一行敘述當場就算完，中間沒有待送出的狀態。

## 各語言生態的資料庫存取分層：手寫 SQL、查詢建構器、ORM

自己寫 SQL、用建構器組 SQL、用 ORM 對應物件，這三層在多數語言生態裡都找得到對應的套件，名字不同而分層一致。

DataFrame 這一層則是額外的第四種，它不在上面那條線上——它處理的是已經在記憶體裡的表格，與資料庫的存取方式無關。一般的增刪改查應用不使用它，那是 ORM 的位置。

## 延伸閱讀：SQL 與 pandas 的寫法對應、運算發生的位置、pandas 的記憶體邊界、ORM 的查詢反模式

**這兩側共用的抽象**：ORM 產生的 SQL 與 DataFrame 的方法，做的是同一組操作。[8.4 SQL 子句與 pandas 方法的對應：篩選、連接、分組彙總、視窗函數，以及空值、索引與順序的語意差異](/python/08-data-analysis/same-relational-algebra/) 給篩選、連接、分組彙總與視窗函數在兩邊的實測比對，以及空值、索引與順序這幾處對應斷掉的位置。

**分界本身**：兩側的差異全部從「運算發生在哪一端」推出來。[8.2 運算發生的位置](/python/08-data-analysis/where-computation-runs/) 寫這條軸怎麼決定容量上限與失敗形態，以及選邊時要問的三個條件。

**選了記憶體端之後的上限**：[8.5 pandas 的記憶體邊界：資料與運算過程的佔用估算，推回資料庫、換引擎與分散式的代價](/python/08-data-analysis/memory-is-the-boundary/) 給資料量的估算方法與越過之後的三個方向。

**ORM 那一側的失敗形態**：延遲載入什麼時候把一次請求變成一百次查詢，在 [backend 模組一的查詢反模式](/backend/01-database/query-anti-patterns/)。那一篇把 N+1 與長交易列成可診斷的清單，並給出每請求的查詢次數預算。
