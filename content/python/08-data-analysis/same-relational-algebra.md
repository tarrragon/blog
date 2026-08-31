---
title: "8.4 SQL 與 DataFrame 是同一套關聯代數的兩個介面"
date: 2026-08-31
description: "想把 SQL 的寫法換算成 pandas 的操作、或想知道這組換算在哪裡會失準時"
weight: 4
tags: ["python", "pandas", "sql", "dataframe", "relational-algebra"]
---

SQL 的子句與 pandas 的方法對應得起來，因為兩者操作的是同一種資料結構：由欄與列構成的表格。對表格能做的基本操作就那幾種——挑出符合條件的列、挑出要的欄、把兩張表按鍵值接起來、把列分組後彙總——這組操作叫關聯代數。SQL 與 DataFrame 各自是它的一個介面——介面在這裡指的是表達那組操作的那一層，底下由誰執行、怎麼執行都被它蓋住。

換介面重寫一次同樣的邏輯因此是划算的練習：邏輯已經想清楚了，剩下的是查另一套語法怎麼寫。

## 四組對應

以下的 `emp` 兩邊是同一份資料，一邊在 SQLite 裡、一邊在記憶體的 DataFrame 裡。

### 挑出符合條件的列

```sql
SELECT name FROM emp WHERE salary > 150
```

```python
emp[emp["salary"] > 150][["name"]]
```

### 把兩張表按鍵值接起來

```sql
SELECT e.name, d.dname FROM emp e JOIN dept d ON e.dept = d.dept
```

```python
emp.merge(dept, on="dept")[["name", "dname"]]
```

### 分組之後彙總

```sql
SELECT dept, MAX(salary) AS m FROM emp GROUP BY dept
```

```python
emp.groupby("dept", as_index=False)["salary"].max().rename(columns={"salary": "m"})
```

### 窗口函數：算出分組的統計值，但保留原本的每一列

```sql
SELECT name, salary - AVG(salary) OVER (PARTITION BY dept) AS d FROM emp
```

```python
emp.assign(d=emp["salary"] - emp.groupby("dept")["salary"].transform("mean"))[["name", "d"]]
```

`transform` 是這一組裡最值得記的：它與 `agg` 的差別正是窗口函數與 `GROUP BY` 的差別——`agg` 讓每一組收斂成一列，`transform` 把組的統計值攤回組內的每一列。

這四組在同一份資料上跑出來的結果逐格相同。

## 對應斷掉的三個位置

有三個地方兩邊的語意本來就不同，照著逐句翻譯會在這裡失準。

**空值在分組時的去留。** SQL 的 `GROUP BY` 把 `NULL` 當成一組，pandas 的 `groupby` 預設把含缺值的那些列整組丟掉。

```python
t.groupby("k").size()                 # {'x': 1}          缺值那一組消失了
t.groupby("k", dropna=False).size()   # {'x': 1, nan: 2}  與 SQL 一致
```

同一段邏輯照著翻譯過來，統計結果會少掉一整組而且不會報錯。這是四組對應之外最容易靜默出錯的一項。

**索引。** DataFrame 的每一列有一個索引，它獨立於欄位存在，而且會在 `groupby`、`merge` 之後改變。SQL 沒有對應的概念。翻譯過來的程式碼常常需要 `reset_index()` 或 `as_index=False`，那幾個呼叫處理的正是索引這個 SQL 沒有的狀態。

**順序。** SQL 的查詢結果在沒有 `ORDER BY` 時不保證順序。DataFrame 的列有位置順序，而且多數操作會保留它。比對兩邊的結果之前要先各自排序，否則比的是兩份排序不同的資料。

## 往下走

**這兩個介面為什麼會分家**：一邊把運算交給資料庫，一邊在自己的記憶體裡算。[8.2 運算發生在哪一端](/python/08-data-analysis/where-computation-runs/) 寫這條分界怎麼決定容量上限，以及選邊要問的三個條件。

**從產出認出手上是哪一個介面**：[8.3 ORM 交出查詢，DataFrame 自己算](/python/08-data-analysis/orm-and-dataframe/) 寫兩者的回傳值形狀差在哪，以及分得開它們的三個訊號。

**這套代數在 SQL 那一側怎麼設計**：關聯代數的組合規則決定了子句的先後、連接的左右與分組的鍵，而那些規則各有一處與直覺相反。[SQL：這個語言為什麼長這樣](/sql/) 從語言的宣告式性質推導這一整組規則，並另外處理文字之外的四方（識別字規則、引擎的寬鬆度、權限、最佳化器）。

**換介面之後接手的新限制**：SQL 那一側沒有記憶體上限的問題，換到 DataFrame 就有了。[8.5 記憶體是 pandas 的邊界條件](/python/08-data-analysis/memory-is-the-boundary/) 給估算方法與越過之後的三個方向。
