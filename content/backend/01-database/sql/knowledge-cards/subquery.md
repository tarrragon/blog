---
title: "Subquery（子查詢）"
date: 2026-08-31
description: "看到括號內嵌有另一個 SELECT，想確認它的求值時機與執行次數時"
aliases: ["/sql/knowledge-cards/subquery/"]
weight: 8
tags: ["sql", "subquery", "correlated", "knowledge-card"]
---

Subquery（子查詢）是寫在另一個查詢內部的巢狀查詢。依是否引用外層欄位可分為兩類，這個差異決定子查詢的邏輯求值次數，也直接影響執行代價——實際的執行次數與掃描方式須透過 [Query Plan（執行計畫）](/backend/01-database/sql/knowledge-cards/query-plan/) 確認。

## 跟其他概念的關係

**獨立子查詢（uncorrelated subquery）** 不依賴外層欄位，可以整段單獨執行；邏輯上只需計算一次，再將結果交給外層比對。`WHERE 顧客編號 IN (SELECT 顧客編號 FROM 訂單)` 括號內即屬於獨立子查詢，先算出訂單表的顧客清單，外層再拿來逐列比對。

**相關子查詢（correlated subquery）** 引用了外層查詢的欄位，脫離外層便無法單獨執行；語意上會針對外層的每一列各求值一次。`WHERE EXISTS (SELECT 1 FROM 訂單 WHERE 訂單.顧客編號 = 顧客.顧客編號)` 屬於相關子查詢（寫成 `SELECT 1` 是因 `EXISTS` 只檢驗是否至少回傳一列、不取用投影值），括號內的 `顧客.顧客編號` 來自外層，因此每位顧客都要各自檢查一次是否存在對應訂單。

閱讀陌生查詢時有一項直接的識別線索：**只要括號內出現外層的表名或別名，這段子查詢在語意上就是逐列執行**。寫在 `WHERE` 條件裡的子查詢只交出比對結果或清單，不會將內層資料表作為 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/) 併入外層的 `FROM` 範圍，這點也是外層 `SELECT` 無法直接讀取內層欄位的原因。反之，寫在 `FROM` 或 `JOIN` 裡並賦予別名的子查詢稱為**派生表（derived table，亦稱 inline view）**，例如 `FROM (SELECT 顧客編號, sum(金額) AS 總額 FROM 訂單 GROUP BY 顧客編號) AS 各顧客`，它產出的中間關係會直接進入外層 `FROM` 範圍，常用於在連接前預先彙總以避免列數膨脹，或在外層以 `WHERE` 篩選視窗函數結果。

## 可觀察訊號與例子

`WHERE` 內的子查詢不會把內層資料表暴露給外層 `SELECT`。執行 `SELECT 姓名, 訂單.金額 FROM 顧客 WHERE 顧客編號 IN (SELECT 顧客編號 FROM 訂單)` 會回傳 `no such column: 訂單.金額`，因為 `訂單` 並未進入外層的 `FROM` 子句。

若要透過子查詢帶出單一欄位值，可將相關純量子查詢寫在 `SELECT` 清單中：`SELECT 姓名, (SELECT 金額 FROM 訂單 WHERE 訂單.顧客編號 = 顧客.顧客編號 ORDER BY 訂單編號 LIMIT 1) FROM 顧客`。純量子查詢每次只能回傳單一純量值，需要取回多欄或多列時仍應改用連接。

## 判斷條件與後果

相關子查詢在內層表缺乏 [Index（索引）](/backend/01-database/sql/knowledge-cards/indexing/) 時成本極高：若最佳化器未將其改寫為連接，外層每一列都會觸發一次內層全表掃描。建立對應索引後，每次查找從全表掃描改為索引定位，同一段查詢的耗時可能縮短數百倍。

獨立子查詢搭配 `NOT IN` 時另有空值陷阱：只要內層清單包含任何一個 [NULL（空值）](/backend/01-database/sql/knowledge-cards/null/)，外層 `NOT IN` 就會靜默回傳零列且不報錯，完整推導與實測見 [SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)。
