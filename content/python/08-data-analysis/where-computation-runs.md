---
title: "8.2 運算發生在哪一端，決定了工具長什麼樣子"
date: 2026-08-31
description: "運算留在資料庫端或搬進記憶體端這條分界，怎麼決定工具的形狀、容量上限與失敗形態"
weight: 2
tags: ["python", "data-analysis", "sql", "orm", "pandas"]
---

整批資料有兩個地方可以算：留在資料庫裡，或搬進程式的記憶體。這條分界決定了工具的形狀、它的容量上限，以及它的失敗形態。本模組其餘各篇的判斷標準都折算回這一條。

## 留在資料庫端：程式送出描述，收回結果

程式送出的是一段描述要算什麼的文字，資料庫收下之後自己完成篩選、合併與彙總，把結果送回來。原始資料從頭到尾沒有進入程式。

Python 這一側有三種寫法，差別只在那段 SQL 由誰組出來。

**自己寫 SQL 字串**：`sqlite3`、`psycopg2` 這類套件遵循 DB-API 這個標準介面，程式把 SQL 交給它，它負責送出與取回。

**用方法串出 SQL**：SQLAlchemy Core 這類查詢建構器提供 Python 的方法對應 SQL 的子句，組出來的仍然是一段 SQL。

**用類別描述表**：[ORM](/backend/knowledge-cards/orm/) 這一類工具（SQLAlchemy、Django ORM）把資料表對應成類別、把資料列對應成物件，篩選條件寫成屬性比較，框架據此組出 SQL，並把回來的每一列包成物件。

三者的共同點比差異重要：**運算在資料庫那一端發生**，程式收到的是算完的結果。編譯出來的 SQL 可以直接印出來看：

```python
from sqlalchemy import select
stmt = select(Customer).where(Customer.age > 18)
print(stmt.compile(engine))
# SELECT customer.id, customer.name, customer.age FROM customer WHERE customer.age > ?
```

## 搬進記憶體端：資料整批進來，程式自己算

另一側的做法是把資料整批載進程式，運算由程式自己完成。pandas 屬於這一側，它的容器是 [DataFrame](/sql/knowledge-cards/dataframe/)。

```python
df[df["age"] > 18]
```

這一行沒有連線、沒有查詢語句、沒有資料庫。`df` 是一張已經在記憶體裡的表格，這一行做的是對一個布林陣列取值。資料的來源可以是資料庫，也可以是 CSV、日誌檔或某個 API 回傳的內容——載進來之後，接下來的每一步運算都寫成一樣的形式，來源是哪一種不再影響寫法。

## 兩端的分工由三個條件決定

**資料量。** 記憶體端要把資料整批放進來，所以容量是硬上限；資料庫端沒有這個限制，它一次只需要把符合條件的部分送回來。

**要算的運算 SQL 表達得出來嗎。** 篩選、合併、分組彙總、排名，SQL 都寫得出來。統計檢定、時間序列的滑動窗口、把資料餵給模型，SQL 寫起來吃力或根本沒有對應語法，這些落在記憶體端。

**算完之後還要做什麼。** 結果如果只是要回傳給使用者或寫回另一張表，留在資料庫端的路徑最短——資料不必先進記憶體再送出去；如果後面還要接繪圖、統計或模型訓練，資料終究要進記憶體，那就沒有理由分兩段做。

實務上的常見形態是兩端接力：用 SQL 把資料量先壓下來，再把壓縮過的結果搬進記憶體做後面的部分。

```python
df = pd.read_sql("SELECT * FROM orders WHERE year = 2024", conn)
# 這一行之後全部在記憶體裡，與資料庫無關
```

## 這條軸有一個刻意模糊它的工具

DuckDB 兩邊都站：它接受 SQL，而查詢的對象可以是記憶體裡的 DataFrame，也可以是磁碟上的檔案。

```python
duckdb.sql("SELECT dept, count(*) c FROM emp GROUP BY dept")  # emp 是一個 DataFrame
```

它把「資料庫」這個角色從一台獨立的伺服器換成同一個程序裡的運算引擎，而軸本身仍在——差別只在資料要不要複製一份進 Python 的記憶體。

## 往下走

**從回傳值認出手上是哪一類**：資料庫端的工具回傳的是物件或資料列，記憶體端的工具回傳的是一張新的表。[8.3 ORM 交出查詢，DataFrame 自己算](/python/08-data-analysis/orm-and-dataframe/) 寫兩者各自產出什麼，以及外觀相似的方法串接底下差了什麼。

**兩端共用的那套抽象**：篩選、合併、分組彙總在兩端都有，而且對應得起來。[8.4 SQL 與 DataFrame 是同一套關聯代數的兩個介面](/python/08-data-analysis/same-relational-algebra/) 給四組對應的實測比對，以及對應斷掉的三個位置。

**記憶體端的容量上限**：[8.5 記憶體是 pandas 的邊界條件](/python/08-data-analysis/memory-is-the-boundary/) 給資料量的估算方法、運算過程額外要的空間，以及越過之後三個方向各自付什麼代價。

**資料庫端那一側的工程議題**：連線池、交易邊界、一次請求該打幾次資料庫，在 [backend 模組一](/backend/01-database/)。那個模組從 N+1 與延遲載入這些形態進去，並給出每請求查詢次數預算當判讀基準。
