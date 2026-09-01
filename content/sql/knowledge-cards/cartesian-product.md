---
title: "Cartesian Product（笛卡兒積）"
date: 2026-09-01
description: "看到 CROSS JOIN、或結果的列數遠多於預期時，查這個運算什麼時候會被展開"
weight: 16
tags: ["sql", "join", "cross-join", "cardinality", "knowledge-card"]
---

笛卡兒積把兩個 [relation](/sql/knowledge-cards/relation/) 的每一列與另一邊的每一列各配一次，得到的關係列數是兩邊列數的乘積。它是[關聯代數](/sql/knowledge-cards/relational-algebra/)的一個運算，而連接由它與選取組合而成：全部組合先在語意上成立，條件再從裡面挑出要留的那些。

SQL 寫成 `CROSS JOIN`，也可以在 `FROM` 裡用逗號把兩張表隔開。

## 條件決定它會不會被展開

代數說連接從積開始，而那是語意層的定義，執行方式由[最佳化器](/sql/knowledge-cards/query-optimizer/)按代價選。條件把兩邊綁起來的時候，它用索引或雜湊直接找出配得上的那些列，全部組合一次都沒有被造出來。

條件缺席的時候展開才會發生。一張逐日的觀測表跟自己做沒有條件的 `CROSS JOIN`：

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

15139881 是 3891 的平方。外層每掃一列，內層就把整張表再走一遍，而這一千五百萬對配對在後面的子句拿到資料之前就要先產生出來。這張表加到 13891 列之後，列數變成 3.6 倍而配對數變成 192959881——**將近十三倍**。成長是平方而非線性，這正是這個運算與其他多出來的列的差別。

**要看的是條件把不把兩邊綁起來，而不是用了哪個關鍵字。** `CROSS JOIN` 加一個等值條件，與 `JOIN ... ON` 寫同一個條件，對引擎是同一段查詢（[1.18](/sql/declared-intent-vs-behaviour/)）；反過來，`JOIN` 寫了而 `ON` 的條件只提到單邊的欄位，展開照樣發生。

## 與列數膨脹是兩種不同的多

結果比預期多的時候有兩個成因，分辨它們決定要改什麼。

[列數膨脹](/sql/join-changes-rows-and-nulls/)是條件正確而一列配到了多列，於是它被複製那麼多次——多出來的量由資料的重複程度決定，改法是把展開的那一層先收成一列，或改用不展開的寫法。笛卡兒積是條件從一開始就沒有把兩邊綁住——多出來的量由兩張表各自的大小決定，改法是補上那個條件。

分辨的問句落在條件上而非結果上：**這個條件把一列綁到對面幾列。** 綁到常數量級（幾列、幾十列）是配對條件，多出來的量由重複程度決定，那是膨脹；綁到與表的大小同量級，那個條件篩掉了一些列，而每一列對面掛著的對象數仍然隨表一起長，多出來的量由兩張表的大小決定，那是積。

「有沒有同時引用兩邊」不足以分辨。`ON a.v > b.v` 同時引用了兩邊，而它把左邊每一列綁到右邊將近一半——`v` 的值互不相同時，一千列得 499500 對、兩千列得 1999000 對，仍然是平方。低基數的等值鍵同理：`ON a.區域 = b.區域` 只有幾個區域時，一千列對一千列得五十萬對。

這裡刻意不問「這一列是靠哪個條件配起來的」——`JOIN` 寫了而 `ON` 只提單邊欄位的那個形態，讀者答得出「靠那個 `ON` 條件」而它並沒有把兩邊配起來，問句會把積判成膨脹。

## 概念位置

笛卡兒積是連接的下限——條件寫得越少，結果越靠近它，而條件寫滿的時候結果落在兩張表配得上的那些列。所以「連接的結果集會不會整個換一個量級」這個問題等於「條件綁住了多少」，與用了 `JOIN` 還是 `CROSS JOIN` 無關。而條件綁不綁得住，由它引用到幾個[表的出現](/sql/table-occurrence-and-alias/)決定——與那個分辨問句是同一件事。

它在[關聯代數](/sql/knowledge-cards/relational-algebra/)裡的位置說明了漏寫連接條件的後果為什麼這麼大：查詢退回它的定義起點，全部組合重新成立。這是結果集大小的整個量級換掉，與逐步變慢是不同的一件事。

## 往下走

條件正確而列數仍然變多的那一種，在 [1.6 連接產出的是新的關係](/sql/join-changes-rows-and-nulls/)。同一批配對用自連接與 `EXISTS` 兩種寫法的差別，在 [1.8 IN、EXISTS 與 JOIN](/sql/in-exists-join/)。`CROSS JOIN` 這個關鍵字對讀的人宣告了什麼，在 [1.18 關鍵字宣告意圖，引擎只執行行為](/sql/declared-intent-vs-behaviour/)。production 查詢的結果集大小怎麼治理，在 [Cardinality Explosion](/backend/knowledge-cards/cardinality-explosion/)。
