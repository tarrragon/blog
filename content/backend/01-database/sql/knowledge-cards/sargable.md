---
title: "Sargable（可走索引的條件形狀）"
date: 2026-09-01
description: "索引已建立但執行計畫仍走全表掃描時，檢驗條件寫法是否阻擋了索引查找"
aliases: ["/sql/knowledge-cards/sargable/"]
weight: 15
tags: ["sql", "index", "query-plan", "performance", "knowledge-card"]
---

語意完全等價的兩種條件寫法會回傳同一批列，但其中一種能讓引擎在 [Query Plan（執行計畫）](/backend/01-database/sql/knowledge-cards/query-plan/) 中執行 [Index（索引）](/backend/01-database/sql/knowledge-cards/indexing/) 查找，另一種則會退回全表掃描。區分這兩種形狀的性質稱為 Sargable（源自 search argument able）：指一個查詢條件能否直接作為索引搜尋的引數。

## 索引查找對具體比對值的要求

索引儲存的是欄位的原始值及其對應的列位置，因此索引查找需要拿一個具體值進去比對。條件寫成 `下單日 = '2024-03-01'` 時，目標值直接出現在條件中，引擎可直接定位。

條件改寫為 `date(下單日) = '2024-03-01'` 時，索引儲存的是 `下單日` 的原始值，但條件比對的是 `date()` 運算後的結果，兩者無法直接對應。引擎必須逐列取出 `下單日` 計算函式結果後才能比對，等於掃描整張表。以下為同一張 50,000 列訂單表與同一個索引的實測計畫：

```text
-- SQLite 3.51，訂單表五萬列（訂單編號 / 顧客編號 / 下單日 / 金額）
-- CREATE INDEX ix_日 ON 訂單(下單日)，查的是 SELECT *
下單日 = '2024-03-01'          SEARCH 訂單 USING INDEX ix_日 (下單日=?)
date(下單日) = '2024-03-01'    SCAN 訂單
```

## 條件形狀的排除範圍與執行計畫確認

索引欄位被包入函式或算術運算時，原 B-Tree 索引無法執行**查找**（引擎頂多把整個索引當成較窄的表從頭掃過，在計畫中顯示為 `SCAN ... USING COVERING INDEX`）。這一步單看條件文字即可判斷：檢查索引欄在條件裡是獨立出現，還是被包進運算式。上方的 `SELECT *` 因索引未涵蓋全部欄位而顯示為 `SCAN 訂單`；若改為只取索引欄與主鍵，兩條計畫都會多出 `COVERING`。常見解法是**額外對同一個運算式（或對應的產生欄）建立運算式索引**，此時命中的是新索引而非原欄位索引。

即使索引欄獨立出現，也不保證一定能走查找。在 B-Tree 索引上，有多類裸欄位寫法仍可能觸發全表掃描：隱式型別轉換（例如對文字欄比對整數而迫使引擎先逐列轉型）、未命中複合索引最左前導欄、萬用字元開頭的比對（`LIKE '%03-01'`）、`OR` 連接另一個無索引欄位，以及 `LIKE '2024-03%'` 這類前綴比對。前綴比對在 SQLite 預設走全表掃描，是因為 SQLite 的 `LIKE` 對 ASCII 預設不區分大小寫，與索引預設採用的 `BINARY` 逐位元組排序規則不符（各家引擎的比對規則對照在 [SQL.15 字串比較與 collation：相等、排序、LIKE 與索引可用性](/backend/01-database/sql/string-comparison-and-collation/)）。對此有兩種解方：在 SQLite 開啟 `case_sensitive_like` 讓引擎辨識，或手動改寫為 `>=` 與 `<` 的範圍條件。在 50,000 列訂單表上實測，原本的 `LIKE '2024-03%'` 走全表掃描，改寫為範圍條件後即改走索引查找，兩者回傳的列完全一致。

因此檢視條件形狀只屬於排除法的第一步，實際執行方式仍須向引擎索取計畫確認。**在無法取得執行計畫的情境下，檢查條件形狀是僅讀 SQL 文字即可先做的靜態排除檢查**——它只需閱讀 SQL 文字，不必連線、不必讀取資料，也不需要建立物件的權限（見 [SQL.16 SQL 的權限模型：角色、GRANT 的授權單位與最小權限](/backend/01-database/sql/privilege-model/)）。

「被函式或運算包住」與「裸欄位仍掃全表」兩類情形的可調整位置不同。**被包住的條件**可透過改寫條件或增建運算式索引解決：改寫成範圍條件會增加閱讀時核對邊界的負擔；將運算移到常數端或建運算式索引不改變語句的直覺讀法，但運算式索引會將成本轉嫁至寫入端（嘗試順序見 [SQL.22 可讀性與執行代價：兩者一致與分岔的情形](/backend/01-database/sql/readable-and-fast-mostly-align/)）。

**裸欄位仍掃全表**的情形，差別在於條件能否劃出 B-Tree 索引上的一段連續區間。前綴比對能對應連續區間，對齊 collation 或改寫成範圍條件後就能查找；隱式型別轉換改為對齊欄位型別即可恢復查找；萬用字元開頭（`LIKE '%03-01'`）的目標散落在 B-Tree 各處，統計資訊再新、選擇率再低都無法走一般 B-Tree 查找，須改換索引類型（例如 PostgreSQL 的 `pg_trgm` GIN／GiST 三元組索引或全文索引）；`OR` 連接無索引欄位則有一半條件不在原索引內，須替另一欄補索引或改寫為 `UNION ALL`。

## 還原可查找形狀的改寫方式

`date(下單日) = '2024-03-01'` 的目標是鎖定單一日期，可改寫為兩端皆為具體值的範圍條件：

```text
下單日 >= '2024-03-01' AND 下單日 < '2024-03-02'
    SEARCH 訂單 USING INDEX ix_日 (下單日>? AND 下單日<?)
```

將運算搬到不含索引欄位的一側同樣有效：`下單日 = date('2024-03-15','-14 day')` 右側先求出常數值，左側欄位維持獨立，計畫即改走索引查找。

若條件本身難以改寫，可讓索引配合條件，改對運算式本身建索引。建立 `CREATE INDEX ix_月 ON 訂單(substr(下單日,1,7))` 後，原本全表掃描的 `substr(下單日,1,7) = '2024-03'` 會變成 `SEARCH 訂單 USING INDEX ix_月 (<expr>=?)`。運算式索引的維護成本同樣由寫入端承擔，而且每次寫入還必須多計算一次該運算式。

## 條件形狀與統計過期的區分

索引存在但引擎未使用時，常見的兩個成因處置完全不同。[Query Statistics（統計資訊）](/backend/01-database/sql/knowledge-cards/query-statistics/) 過舊時，條件本身已可走索引，只是最佳化器估錯成本而放棄，重收統計即可改善；條件把索引欄包進函式時，引擎根本無法利用原索引查找，統計再新也無效，必須修改條件或另建運算式索引。

驗證成因的方式是將條件改寫成裸欄位形狀後重新觀察計畫：若計畫隨之改走索引，表示原本是條件形狀擋住了索引；若計畫依然沒變，表示路徑一直存在，而是最佳化器依統計判斷走索引不划算。

## 跟其他概念的關係

[SQL.17 查詢的代價：資料分布、索引與寫法各自的影響](/backend/01-database/sql/cost-lives-in-the-plan/) 指出執行代價主要由資料分布與索引決定、而非語法寫法，這張卡即為該結論的明確邊界。邊界非常窄：寫法在這裡只決定引擎**能否使用**既有 [Index（索引）](/backend/01-database/sql/knowledge-cards/indexing/)，至於 [Query Optimizer（查詢最佳化器）](/backend/01-database/sql/knowledge-cards/query-optimizer/) 在多條可行路徑中挑選哪一條，依然由資料分布與統計資訊決定。

## 延伸閱讀：索引機制、執行計畫與取捨

- 索引結構與寫入成本：[Index（索引）](/backend/01-database/sql/knowledge-cards/indexing/)
- `SCAN` 與 `SEARCH` 等執行計畫術語判讀：[Query Plan（執行計畫）](/backend/01-database/sql/knowledge-cards/query-plan/)
- 索引與資料分布改變時的耗時排名實測：[SQL.17 查詢的代價：資料分布、索引與寫法各自的影響](/backend/01-database/sql/cost-lives-in-the-plan/)
- 易讀寫法與可走索引寫法分岔時的調整策略：[SQL.22 可讀性與執行代價：兩者一致與分岔的情形](/backend/01-database/sql/readable-and-fast-mostly-align/)
