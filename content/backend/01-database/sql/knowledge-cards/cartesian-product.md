---
title: "Cartesian Product（笛卡兒積）"
date: 2026-09-01
description: "讀到 CROSS JOIN，或連接查詢回傳列數遠高於預期且呈平方成長時"
aliases: ["/sql/knowledge-cards/cartesian-product/"]
weight: 16
tags: ["sql", "join", "cross-join", "cardinality", "knowledge-card"]
---

將兩個 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/) 的每一列兩兩配對一次，產出列數等於兩表列數乘積的運算稱為 Cartesian product（笛卡兒積）。在 [Relational Algebra（關聯代數）](/backend/01-database/sql/knowledge-cards/relational-algebra/) 中，連接（join）在語意上由笛卡兒積加上條件選取組合而成；在 SQL 中以 `CROSS JOIN` 或在 `FROM` 以逗號並列兩張表表達。

## 配對條件與是否展開的關係

笛卡兒積加選取屬於語意定義，引擎的實際執行方式由 [Query Optimizer（查詢最佳化器）](/backend/01-database/sql/knowledge-cards/query-optimizer/) 依成本決定。當查詢附帶將兩表綁在一起的等值條件時，最佳化器會直接以索引或雜湊查找配對列，不會實際展開全部組合。

唯有缺乏有效配對條件時，完整展開才會發生。以下以逐日氣溫表與自身做無條件 `CROSS JOIN` 實測：

```sql
CREATE TABLE Weather (id INTEGER PRIMARY KEY, recordDate TEXT, temperature INT);
WITH RECURSIVE n(i) AS (SELECT 0 UNION ALL SELECT i+1 FROM n WHERE i < 3890)
INSERT INTO Weather SELECT i, date('2015-01-01', i || ' day'), i % 40 FROM n;
CREATE UNIQUE INDEX ix ON Weather(recordDate);
```

```text
-- SQLite 3.51，Weather 表 3891 列
SELECT count(*) FROM Weather a CROSS JOIN Weather b;
-- 15139881

|--SCAN a USING COVERING INDEX ix
`--SCAN b USING COVERING INDEX ix
```

3891 列自做笛卡兒積產出 15,139,881（3891 的平方）對配對；表長增至 13,891 列（3.6 倍）時，配對數增至 192,959,881（近 13 倍），呈平方級成長。

展開與否取決於條件是否約束了兩表之間的對應關係，而非取決於連接關鍵字。`CROSS JOIN` 搭配 `WHERE` 等值條件與 `JOIN ... ON` 寫相同條件對引擎等價（見 [SQL.21 關鍵字的宣告與引擎的行為：宣告落空的形態與查證](/backend/01-database/sql/declared-intent-vs-behaviour/)）；反之，寫成 `JOIN` 但 `ON` 條件只提及單側欄位時，兩表依然完全展開。

## 與列數膨脹的區別

查詢結果列數超出預期時，成因分為列數膨脹與笛卡兒積，兩者對應不同修法。

[SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/) 說明的列數膨脹是條件正確、但鍵值一對多導致單列被複製多次，多出的列數取決於重複度，修法是先彙總再連接或改用半連接；笛卡兒積則是條件未有效約束兩表配對，多出的列數隨兩表大小相乘成長，修法是補上正確的配對條件。

分辨兩者的判斷標準是「條件把左表每一列綁到右表幾列」：綁到常數量級屬於配對條件（超額列數為膨脹）；綁到與表大小同量級則屬於積（即使條件同時引用兩張表亦然）。例如 `ON a.v > b.v` 在值互異的千列表上仍產出 499,500 對、兩千列表產出 1,999,000 對，呈平方成長；低基數等值鍵（如只有少數區域值的 `ON a.區域 = b.區域`）在千列表對千列表同樣產出數十萬對。

## 跟其他概念的關係

在 [Relational Algebra（關聯代數）](/backend/01-database/sql/knowledge-cards/relational-algebra/) 中，笛卡兒積是連接結果大小的上限：條件越鬆越接近笛卡兒積，漏寫連接條件會使查詢直接退回語意起點，結果集大小躍升一個量級。結果集大小取決於條件約束了幾個表出現（見 [SQL.7 表的出現與別名：表名的指稱、別名的作用範圍與自連接](/backend/01-database/sql/table-occurrence-and-alias/)）以及鍵的選擇率，與關鍵字寫成 `JOIN` 或 `CROSS JOIN` 無關。

## 延伸閱讀：列數膨脹、半連接與結果集治理

- 一對多配對造成的列數膨脹與聚合修法：[SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)
- 自連接與 `EXISTS` 的執行代價實測：[SQL.17 查詢的代價：資料分布、索引與寫法各自的影響](/backend/01-database/sql/cost-lives-in-the-plan/)
- 結果列數上限為左表列數的運算：[Semi-join 與 Anti-join（半連接與反連接）](/backend/01-database/sql/knowledge-cards/semi-join-and-anti-join/)
- `CROSS JOIN` 的關鍵字宣告與執行計畫對照：[SQL.21 關鍵字的宣告與引擎的行為：宣告落空的形態與查證](/backend/01-database/sql/declared-intent-vs-behaviour/)
- 正式環境結果集大小治理：[Query Cardinality Explosion](/backend/knowledge-cards/cardinality-explosion/)
