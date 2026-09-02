---
title: "Cardinality 與 Selectivity（基數與選擇率）"
date: 2026-09-02
description: "看到「這一欄基數太低、索引沒用」，或想知道最佳化器憑什麼決定要不要走索引時，查這兩個數各自量什麼"
weight: 19
tags: ["sql", "cardinality", "selectivity", "index", "query-optimizer", "knowledge-card"]
---

基數是一個集合裡有幾個成員。這個詞在 SQL 裡落在兩個地方：一份 [relation](/sql/knowledge-cards/relation/) 的基數是它有幾列，一個欄位的基數是它有幾個相異值。兩者是同一個定義用在不同的集合上——欄位的基數就是把那一欄單獨取出來、去掉重複之後的列數。

**「基數」這個譯名在站內還有另外三個所指。** 資料建模那一側說的是兩張表之間的關係屬於一對一、一對多還是多對多；查詢結果那一側說的是一段查詢回幾列（[Cardinality Explosion](/backend/knowledge-cards/cardinality-explosion/)）；監控那一側說的是一個指標有幾種標籤組合。本卡與最佳化器讀的都是上一段那個計數義，其餘幾個只是共用一個譯名。

選擇率是一個條件留下多少比例的列。它是條件的屬性而非欄位的屬性：`狀態 = '已完成'` 與 `狀態 = '已取消'` 寫在同一欄上，而兩者的選擇率可以差一個量級以上——下一節那組資料裡是十八倍。

兩者在等值條件上有一個關係：值分布均勻的時候，`欄 = 某值` 的選擇率大約是相異值個數的倒數。分布不均勻的時候這個估算失準，而那正是[統計資訊](/sql/knowledge-cards/query-statistics/)要另外記下最常出現的幾個值的原因。

## 同一個索引，最佳化器對不同的值做相反的決定

二十萬列的訂單表，`狀態` 只有兩個值（已完成佔九成五、已取消佔半成），`顧客編號` 有五萬個值。兩欄各建一個索引，跑過 `ANALYZE`（收集統計的那道指令）之後問同一種等值條件：

```text
-- PostgreSQL 18
SELECT 備註 FROM 訂單 WHERE 狀態 = '已完成';     -- Seq Scan（索引沒被用）
SELECT 備註 FROM 訂單 WHERE 狀態 = '已取消';     -- Index Scan using ix狀態
SELECT 備註 FROM 訂單 WHERE 顧客編號 = 12345;    -- Index Scan using ix顧客
```

同一個 `ix狀態`，同一種條件形狀，兩個值得到相反的決定。走索引要先讀索引拿到位置、再回原表取 `備註` 這一欄，每一列付兩次；命中九成五的列時，這筆帳輸給從頭讀一遍。

引擎的依據寫在統計裡，而那份摘要是看得到的：

```text
SELECT attname, n_distinct, most_common_freqs FROM pg_stats WHERE tablename = '訂單';
 狀態     |       2    | {0.94996667,0.050033335}
 顧客編號 | -0.25113   |
```

`n_distinct` 是基數，`most_common_freqs` 是那幾個值各自的選擇率。**這兩欄是抽樣估出來的，每跑一次 `ANALYZE` 都會在小數後幾位變動**——真值是 0.95 與 0.05，而印出來的從來不是整數。`顧客編號` 那一格的負數是另一種寫法——絕對值小於一時代表「相異值個數是總列數的這個比例」，0.25 乘二十萬約等於五萬。

**這兩個數是估計而不是事實。** 它們來自上一次收集統計的那一刻，所以同一段查詢在資料變動之後可能換一個計畫，而查詢的文字一個字都沒改（[Query Statistics](/sql/knowledge-cards/query-statistics/)）。

## 同一份統計，各家的取捨不同

上面那組表搬到 SQLite 3.51，`ANALYZE` 跑過之後三段查詢全部走索引，包含命中九成五的那一段。SQLite 的 `sqlite_stat1` 記下的數字與 PostgreSQL 量到的是同一件事：

```text
訂單 / ix狀態 → 200000 100000     -- 二十萬列，每個相異值平均十萬列
訂單 / ix顧客 → 200000 4          -- 二十萬列，每個相異值平均四列
```

所以「基數低的欄位上索引沒用」這句話要分兩半聽：低基數確實讓多數值的選擇率變高，而**要不要因此放棄索引是最佳化器的判斷，各家的門檻不同**。可攜的說法是選擇率，不是計畫。

## 概念位置

**這兩關的成本模型建在一個前提上：資料按列存放，而索引是另一份按鍵排好的結構，走它要回原表取其餘欄位。** 欄式引擎（DuckDB、以及讀 parquet 這一類）不是這個形狀——它按欄讀、靠區塊的最大最小值跳過整段，沒有逐列回表那筆帳，所以「命中九成五就別走索引」在那裡不成立，對應的手段是資料的排序與分區。下面兩關針對的是前一種。

選擇率與 [sargable](/sql/knowledge-cards/sargable/) 是索引派不派得上用場的兩個獨立條件。sargable 問的是條件的**形狀**能不能翻成索引上的一次查找——欄位被函式包住就翻不了。**這一關過不了不等於索引沒用**：條件裡用到的欄位都在索引上的時候，引擎仍然可能整個掃過索引再逐列過濾，省下的是回原表那筆帳（PostgreSQL 印成 `Index Only Scan` 加一個 `Filter`，SQLite 印成 `SCAN ... USING COVERING INDEX`）。所以兩關管的是不同的索引用法，而不是同一種用法的兩道閘。選擇率問的是通過查找之後**還剩多少列**——形狀對而留下的列佔了大半，最佳化器仍然會選擇不走它。兩關都過，[索引](/sql/knowledge-cards/indexing/)才換得到速度。

基數也決定連接之後的列數。低基數的欄位當連接鍵時，一列會配到對面同一個值的所有列，而那個數量隨表一起長——這是[笛卡兒積](/sql/knowledge-cards/cartesian-product/)那張卡分辨「積」與「膨脹」時用的同一個量。

## 往下走

這兩個數怎麼被收集、多久失效一次，在 [Query Statistics（統計資訊）](/sql/knowledge-cards/query-statistics/)。[query optimizer](/sql/knowledge-cards/query-optimizer/) 拿它們估代價的過程，以及估錯時計畫長什麼樣，在 [Query Plan（執行計畫）](/sql/knowledge-cards/query-plan/)。同一道題三種寫法的排名怎麼隨索引重排，在 [1.16 代價由資料與索引決定](/sql/cost-lives-in-the-plan/)。production 上結果集大小怎麼治理，在 [Cardinality Explosion](/backend/knowledge-cards/cardinality-explosion/)。
