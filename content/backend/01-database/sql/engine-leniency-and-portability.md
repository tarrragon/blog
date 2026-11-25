---
title: "SQL.19 引擎寬鬆度與可攜性：各家對同一組寫法的差異、分級與處理時機"
date: 2026-09-02
description: "SQLite、DuckDB、PostgreSQL 與 MySQL 在未分組欄位、WHERE 用別名、同表未取別名、字串比對與空值排序上的實測對照，當場報錯至靜默無差異的分級，以及依目標組態數決定處理時機的原則"
aliases: ["/sql/engine-leniency-and-portability/"]
weight: 20
tags: ["sql", "portability", "engine", "standard", "compatibility"]
---

同一段 SQL 送進 SQLite、DuckDB、PostgreSQL 與 MySQL 時，各家引擎接受與拒絕的邊界互不相同。本篇先以跨引擎實測對照各家寬鬆度，依發聲位置將差異分為當場報錯、等資料才報錯、靜默而輸出不同與靜默且輸出相同等層級；接著界定可攜性的操作對象，說明如何依目標組態數與切換控制權決定處理時機，並列出組態清單、連線設定與測試環境等成立前提。

SQL 標準留有許多未明文規定的空間，各家 [Database Engine（資料庫引擎）](/backend/01-database/sql/knowledge-cards/database-engine/) 在實作時各自補上決定。**寬鬆度**指的是當查詢不合標準或標準未規定時，引擎接受該寫法並代為補上決定的程度。在查詢文字之外影響結果的各項因素中——識別字規則、collation、權限、約束、最佳化器與部署形態——寬鬆度決定的是這些項目各自接受與拒絕的界線，因此會同時表現在名稱解析、字串比對、分組與排序等多個位置。

以下實測執行於四家引擎：SQLite 3.51、DuckDB v0.10.3、PostgreSQL 18、MySQL 8.4。測試表各含兩列，五段查詢與輸出如下：

```sql
CREATE TABLE 顧客 (顧客編號 INT, 姓名 VARCHAR(20));
CREATE TABLE 訂單 (訂單編號 INT, 顧客編號 INT, 金額 INT);
INSERT INTO 顧客 VALUES (1, 'Anna'), (2, 'anna');
INSERT INTO 訂單 VALUES (101, 1, 700), (102, 1, NULL);

-- 未分組欄位：訂單編號不在 GROUP BY 裡，也沒有被聚合
SELECT 顧客編號, 訂單編號 FROM 訂單 GROUP BY 顧客編號;
-- SQLite：1 101（這一組有兩列，它挑了其中一列）
-- DuckDB、PostgreSQL、MySQL：拒絕
-- MySQL 在同一條連線先 SET SESSION sql_mode = '' 之後：1 101

-- WHERE 用別名：兩倍在 SELECT 那一步才算出來
SELECT 金額 * 2 AS 兩倍 FROM 訂單 WHERE 兩倍 > 0;
-- SQLite、DuckDB：1400
-- PostgreSQL、MySQL：拒絕

-- 同表未取別名
SELECT count(*) FROM 訂單, 訂單;
-- SQLite：4；引用欄位時才拒，SELECT 訂單編號 FROM 訂單, 訂單 回 ambiguous column name
-- DuckDB、PostgreSQL、MySQL：FROM 就拒絕，連 count(*) 都不收

-- 字串比對
SELECT 姓名 FROM 顧客 WHERE 姓名 = 'anna';
-- SQLite、DuckDB、PostgreSQL：anna
-- MySQL：Anna、anna（預設 collation 不分大小寫）

-- 空值排序
SELECT 訂單編號 FROM 訂單 ORDER BY 金額;
-- SQLite、MySQL：102、101（空的排最前）
-- DuckDB、PostgreSQL：101、102（空的排最後）
```

## 同一組寫法在各家引擎上收與不收的分割

將上述五種寫法並排對照四家引擎的反應，每種寫法都把四家切成兩組，且切法互不一致：

| 寫法         | 語法形態                                                                                 | SQLite         | DuckDB      | PostgreSQL  | MySQL       |
| ------------ | ---------------------------------------------------------------------------------------- | -------------- | ----------- | ----------- | ----------- |
| 未分組欄位   | `GROUP BY` 之外的欄位進 `SELECT`                                                         | 接受           | 拒絕        | 拒絕        | 拒絕        |
| WHERE 用別名 | `SELECT` 的別名用在 `WHERE`                                                              | 接受           | 接受        | 拒絕        | 拒絕        |
| 同表未取別名 | 同一張表出現兩次沒取別名                                                                 | 引用該欄位才拒 | FROM 就拒絕 | FROM 就拒絕 | FROM 就拒絕 |
| 字串比對     | `WHERE 姓名 = 'anna'`                                                                    | 回 1 列        | 回 1 列     | 回 1 列     | 回 2 列     |
| 空值排序     | `ORDER BY 金額`（一列為 [NULL（空值）](/backend/01-database/sql/knowledge-cards/null/)） | 空的排最前     | 空的排最後  | 空的排最後  | 空的排最前  |

任一寫法的分組結果都無法預測下一個寫法：未分組欄位只有 SQLite 接受；`WHERE` 用別名變成 SQLite 與 DuckDB 接受；字串比對只有 MySQL 給出不同結果；空值排序又分成 SQLite 加 MySQL 對上 DuckDB 加 PostgreSQL。即使同表未取別名與未分組欄位的分組相同（SQLite 對上其餘三家），也不保證第三個寫法維持同一分組。

同一家引擎在不同設定下也會分屬接受與拒絕兩側。MySQL 預設拒絕未分組欄位，但清空 `sql_mode` 後同一段查詢即回傳 `1 101`——寬鬆度的最小單位是「引擎版本加上設定組態」，而不只是引擎名稱。此外，SQLite 接受未分組欄位時並非單純放行，而是自行從多列中挑選一列的值回傳，挑選依據由執行計畫決定且未寫在查詢中（多列分組的實例見 [SQL.9 分組鍵的選擇：鍵與一組所代表的對象](/backend/01-database/sql/grouping-key-decides-the-unit/)）。

單就「接受或拒絕」而言，SQLite 確實比 PostgreSQL 寬鬆；但字串比對與空值排序屬於「四家全部接受但結果不同」的類別。若只預期「從寬鬆引擎遷移至嚴格引擎會報錯」，會直接漏掉這類完全不報錯但輸出改變的差異。

各寫法的完整機制分別在所屬篇章展開：`WHERE` 用別名與列條件放進 `HAVING` 見 [SQL.2 子句的求值順序：每一步可用的欄位、語意模型擋下的寫法與各家引擎放寬的寫法](/backend/01-database/sql/clause-evaluation-order/)，分組後輸出非分組欄位見 [SQL.9 分組鍵的選擇：鍵與一組所代表的對象](/backend/01-database/sql/grouping-key-decides-the-unit/)，同表未取別名見 [SQL.7 表的出現與別名：表名的指稱、別名的作用範圍與自連接](/backend/01-database/sql/table-occurrence-and-alias/)，字串比對見 [SQL.15 字串比較與 collation：相等、排序、LIKE 與索引可用性](/backend/01-database/sql/string-comparison-and-collation/)，空值排序見 [SQL.11 查詢結果的列序：沒有 ORDER BY 時的來源與 ORDER BY 的規定範圍](/backend/01-database/sql/relations-have-no-order/)。未列於上表但同樣隱蔽的是識別字大小寫：SQLite 與 DuckDB 不區分引號內外的大小寫，遷移至 PostgreSQL 時混用引號的識別字會成批報錯找不到表，詳見 [SQL.14 識別字的規則：各家的大小寫摺疊、引號與保留字](/backend/01-database/sql/identifier-rules/)。

## 跨引擎差異的分級：當場報錯、等資料才報錯、靜默而輸出不同、靜默且輸出相同

跨引擎差異依單一交易、無並行交錯的正常執行路徑中「是否回報錯誤及在哪個時機回報」分為四級。比較的對象是完整**組態**（特定引擎版本配上特定設定）：同一引擎跨大版本升級或更換連線設定，同樣會觸發以下各級差異。若跨引擎切換同時改變了並行寫入模型（例如從 SQLite 單寫入鎖換到 PostgreSQL 多連線並行），直到併發交易交錯才靜默寫壞資料的競態不屬於單句執行差異，須另依 [SQL.20 引擎的部署形態與 SQL 構造：SQLite 與 PostgreSQL 在並行寫入、連線協調與身分上的差異](/backend/01-database/sql/deployment-shape-and-sql-constructs/) 排查。

**當場報錯（剖析或名稱解析即中止）。** 未分組欄位與 `WHERE` 用別名從寬鬆引擎移至嚴格引擎時屬於此級：首次執行立刻報錯並指名欄位，發現最早、最不易遺漏。

**等資料才報錯（特定資料寫入或執行時才中止）。** [Constraint（約束）](/backend/01-database/sql/knowledge-cards/constraint/) 相關差異常屬此級：遷移後查詢照常執行，直到第一筆違反約束的資料寫入才觸發報錯。由於測試資料往往未涵蓋觸發違規的邊界紀錄，這類差異容易在正式環境才浮現。

**靜默而輸出不同（不報錯但結果集合改變）。** 字串比對與空值排序屬於此級：四家引擎全數執行成功且回傳格式正常的列，但內容不同。偵測這類差異必須將同一批查詢在目標組態分別執行並逐列比對輸出；因為兩端都不報錯，團隊不會被系統主動提醒。

**靜默且輸出相同（不報錯且查詢輸出一致）。** [SQL.18 外鍵與參照完整性：宣告、生效與查詢得到的保證](/backend/01-database/sql/foreign-key-and-referential-integrity/) 中 MySQL 8.4（及之前版本）忽略欄位層 `REFERENCES`（MySQL 9.0 起才改為強制執行）或 MyISAM 忽略外鍵即屬此級：建表與查詢全部成功、輸出完全相同，差異只存在於系統目錄（資料庫內建用來記錄表、欄、約束與權限定義的系統表）裡，必須主動查詢系統目錄才會發現。

這四個級別衡量的是**發現時機**，而非嚴重程度或修復工時。當場報錯的差異可能需要重寫大量查詢，靜默且輸出相同的差異可能只需加上一行設定；在偵測成本上，靜默且輸出相同只要查一次系統目錄即可確認，靜默而輸出不同反而需要持續做跨引擎輸出比對。分級的價值在於決定準備順序：當場報錯會在遷移執行時自動現身，靜默且輸出相同則絕不會自己暴露，必須在遷移前的盤點階段主動檢查（遷移的分階段、雙寫與切換流程見 [1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/)）。

## 可攜性的操作對象：引擎代為決定的位置與把決定寫出來的宣告

單獨檢視一段 SQL 文字無法判定它是否具備可攜性，因為差異來自文字未寫明、交由引擎預設補上的決定。將比較規則顯式寫進欄位宣告後，開場實測中的字串等值比對在四家引擎的輸出即可統一（見 [SQL.15 字串比較與 collation：相等、排序、LIKE 與索引可用性](/backend/01-database/sql/string-comparison-and-collation/)）；雖然答案統一，DDL 語法本身仍須依引擎撰寫，且 PostgreSQL 的非確定性規則另有查詢限制：

```sql
-- 分大小寫：WHERE 姓名 = 'anna' 在四家都回 1 列
姓名 TEXT COLLATE BINARY                      -- SQLite
姓名 TEXT COLLATE C                           -- DuckDB；寫 COLLATE BINARY 是語法錯誤
姓名 TEXT COLLATE "C"                         -- PostgreSQL
姓名 VARCHAR(20) COLLATE utf8mb4_0900_as_cs   -- MySQL

-- 不分大小寫：同一句在四家都回 2 列
姓名 TEXT COLLATE NOCASE                      -- SQLite
姓名 TEXT COLLATE NOCASE                      -- DuckDB
姓名 TEXT COLLATE ci                          -- PostgreSQL，ci 要先建成一條非確定性的規則：
    -- CREATE COLLATION ci (provider = icu, locale = 'und-u-ks-level2', deterministic = false);
    -- 注意：PostgreSQL 17 及以前對 deterministic = false 欄位跑 LIKE／正規表示式會直接報錯，
    -- 且不支援 text_pattern_ops 前綴索引；若須跨引擎共用 DDL 並保留 LIKE 索引，應採寫入時正規化
姓名 VARCHAR(20) COLLATE utf8mb4_0900_ai_ci   -- MySQL
```

若系統要求跨引擎共用同一套 DDL、又不希望受限於 PostgreSQL 非確定性 collation 對 `LIKE` 與前綴索引的限制，可改採 [SQL.15 字串比較與 collation：相等、排序、LIKE 與索引可用性](/backend/01-database/sql/string-comparison-and-collation/) 說明的寫入時正規化（統一轉小寫存欄並直接等值比對）。空值排序同樣可透過顯式表達收回引擎的預設決定：

```sql
SELECT 訂單編號 FROM 訂單 ORDER BY (金額 IS NULL), 金額;
-- 四家都回 101、102：金額 IS NULL 對空的那一列是真，真排在假後面
SELECT 訂單編號 FROM 訂單 ORDER BY 金額 NULLS LAST;
-- SQLite、DuckDB、PostgreSQL：101、102
-- MySQL 8.4：ERROR 1064 語法錯誤
```

可攜性檢查的核心問句是：**這段 SQL 是否留有未寫明、交由接收引擎代為補上的決定**。凡是存在這類位置，該處就是潛在的可攜性斷點。這條判斷標準只涵蓋引擎代為決定的層面；查詢是否符合業務需求屬於另一層，任何引擎設定都無法介入（見 [SQL.13 查詢的合法性與答案的正確性：引擎檢查的範圍、答案錯掉的成因與查證方法](/backend/01-database/sql/well-formed-is-not-correct/)）。

正因為問題出在「未寫明而由引擎組態補上」，可攜性在單一組態下無法測出：同一段查詢在固定組態跑一萬次，引擎補上的決定每次都相同。即使在同一個 MySQL 實例上，一條連線清空 `sql_mode`、另一條維持預設，同一段帶未分組欄位的查詢一邊回傳結果、一邊回報 `ERROR 1055`。可攜性是「查詢與目標組態集合」之間的關係，不是查詢文字單獨的屬性。

## 寫的當下要處理哪幾級差異：依目標組態數與切換控制權決定的做法

全面照最嚴格標準撰寫所有查詢需要付出代價：每個可省的預設值都須顯式寫出、語句變長、開發者必須熟記各家預設。是否提前付出這筆成本，取決於**這段 SQL 目前運行的目標組態數**（組態指引擎版本加上設定；同引擎升級大版本或改動連線設定同樣算新增組態）。

當目標組態數為 1 時，須再確認**組態數是否可能因外部要求而增加**（例如客戶指定部署資料庫或強制升級）；組態數已大於 1 時則不需再問。資料庫由團隊自主選定的單一組態系統可延後處理跨引擎成本，由客戶指定資料庫的系統則無法延後。

**單一組態且更換權在團隊自身**：寬鬆度可視為開發便利，處理成本延後至確定遷移當日。遷移當天的工作量取決於靜默而輸出不同與靜默且輸出相同兩級差異的數量（當場報錯會在首次執行自動浮現），主要風險在於延後處理的同時也未留存需要盤點的差異清單。

**單一組態但更換時機取決於外部**（如客戶端部署或排程上的大版本升級）：在撰寫當下提前處理「靜默而輸出不同」與「靜默且輸出相同」兩級差異，顯式寫出 collation、空值排序位置與識別字引號；「當場報錯」級差異可保留至遷移時再改，因為它會立即現身。此策略以增加少量語句長度換取將靜默風險前移至撰寫當下。

**多組態並行**（產品部署在客戶各自的資料庫，或測試與正式環境使用不同引擎）：除顯式寫出決定外，還須建立跨引擎對照測試，將同一批查詢在各目標組態執行並比對輸出。此作法具持續維護成本，但能系統性攔截靜默而輸出不同的差異。若因授權或環境限制無法取得全部客戶組態，則對團隊手邊擁有的組態執行對照，並明文列出已驗證通過的組態清單。跨引擎一致性無法以人工閱讀代替實跑，原因與 [SQL.21 關鍵字的宣告與引擎的行為：宣告落空的形態與查證](/backend/01-database/sql/declared-intent-vs-behaviour/) 相同：宣告是否與執行相符須由實際執行驗證。

**透過查詢建構器或 ORM 封裝 SQL** 則不按組態數分類，而是將決定權轉移給套件層：套件仍須替各家引擎補上這些決定，但實作細節常隱藏在框架內部而不顯露於查詢文字。這項選擇改變的是「由誰負責查核這些引擎預設位置」，並未消除位置本身。

## 按組態數做的選擇成立的前提：組態清單、引擎設定與測試環境

依目標組態數選定的策略建立在三個前提上，任一前提變動時都應重新評估。

**目標組態清單可能擴大。** 維持一致的成本會隨組態數倍數放大：即使查詢數不變，每增加一個目標組態就增加一整輪跨組態對照與驗證。外部事件（客戶指定資料庫、併購其他系統或大版本升級）常擴大清單；其中大版本升級容易被忽略，因為看似未更換引擎，但 `sql_mode` 等設定的預設值常隨大版本調整而改變寬鬆邊界。當清單擴大並啟動遷移時，還需涵蓋資料搬運、雙寫與切換驗證（遷移證據格式示範見 [1.7 Schema Migration Rollout 證據（Schema Migration Rollout Evidence）實作示範](/backend/01-database/schema-migration-rollout-evidence/)）。

**引擎設定可能在連線層變動。** 例如 MySQL 的 `sql_mode` 可於單條連線修改，同一資料庫與同一查詢在不同連線設定下會得到不同結果。這類設定既不在查詢文字裡也不在 schema 定義裡，單看程式碼無法察覺。

**測試環境與正式環境分屬不同引擎時，等價於未受監測的多組態運行。** 測試跑 SQLite、正式跑 PostgreSQL 是常見的異質配對，會使靜默而輸出不同與靜默且輸出相同的差異延遲至正式環境才暴露。此外，兩者在並行寫入模型上也有根本差異：SQLite 序列執行寫入 [Transaction（交易）](/backend/knowledge-cards/transaction/)，PostgreSQL 允許並行寫入。應用程式裡先讀後寫的交易在 SQLite 搭配 `BEGIN IMMEDIATE` 可正常運作，搬至 PostgreSQL 預設隔離等級下卻會在並行時寫出重複資料，[SQL.20 引擎的部署形態與 SQL 構造：SQLite 與 PostgreSQL 在並行寫入、連線協調與身分上的差異](/backend/01-database/sql/deployment-shape-and-sql-constructs/) 記錄了兩家的並行實測與對應構造。

## 跨引擎的一致之外：文字與引擎行為的一致

本篇聚焦於跨組態一致性，即同一段 SQL 送進不同引擎組態後的表現。同一段查詢還面對另一層一致性：關鍵字向後續維護者宣告的預期與引擎實際執行的行為是否相符，[SQL.21 關鍵字的宣告與引擎的行為：宣告落空的形態與查證](/backend/01-database/sql/declared-intent-vs-behaviour/) 分析了各類宣告落空與降級重跑查證法。
