---
title: "SQL：這個語言為什麼長這樣"
breadcrumb: "SQL"
date: 2026-08-31
description: "SQL 的設計而不是它的語法表：子句為什麼這樣切、一個查詢該怎麼讀，以及代價落在哪裡"
weight: 33
tags: ["sql", "database", "query"]
---

本分類處理 SQL 的設計而不是它的語法表。逐個子句怎麼用、有哪些函式，網路上的資料已經足夠；這裡回答的是為什麼子句這樣切、一個查詢該怎麼讀，以及代價藏在哪裡。

## 讀者定位

寫得出基本的 `SELECT` 與 `JOIN`，但沒有系統性地理解這個語言為什麼是這個形狀。讀完之後能把一段陌生的查詢讀準——說得出它保留了哪些列、哪個條件在哪一步生效——並知道結果正確與跑得夠快是兩件要分開驗的事。

本分類反覆用到的兩個字照台灣的講法：**列**（row）指橫向的一筆資料，**欄**（column）指縱向的一個位置。簡體中文的 SQL 資料多半用「行」指這裡的列、用「列」指這裡的欄，兩套剛好對調，[relation](/sql/knowledge-cards/relation/) 那張卡開頭有同一句。

**想把一段陌生的查詢讀準**，四篇走完就夠：[1.2](/sql/clause-evaluation-order/) 每一步手上有什麼、[1.4](/sql/join-left-operand-accumulates/) 連接鏈的左邊是什麼、[1.5](/sql/on-describes-where-filters/) 條件在哪一步生效、[1.20](/sql/declared-intent-vs-behaviour/) 文字說的話跟查詢的行為對不對得上。

**從 [DataFrame](/sql/knowledge-cards/dataframe/) 那一側過來、沒寫過 SQL 的讀者**：[1.1](/sql/declarative-not-procedural/) 不預設 SQL 經驗，它講的是這個語言與逐步執行的程式差在哪。讀完它再回這張表挑落點。

## 推導源頭

**SQL 是宣告式的：寫下的是要什麼結果，而怎麼算、名字指向誰、送出的人被允許做什麼都不在那段文字裡。** 各篇的判斷標準都折算回這一條，而它分出三支，本分類的章節照三支排列。

**第一支問「結果集由什麼決定」。** 答案是一個明確的模型，而那個模型與直覺不同——子句的先後、配對關係寫在哪、連接的左右、條件擺哪一邊、分組的鍵、輸出的單位收不收起來、那批列排成什麼樣，每一項都由[關聯代數](/sql/knowledge-cards/relational-algebra/)的組合規則定死，而每一項的規則都有一處與讀者的直覺相反。這一支要學的就是那個模型，而它的收尾一篇處理直覺錯掉之後會發生什麼——[1.13](/sql/well-formed-is-not-correct/) 說明引擎驗的是這段文字合不合法，「問對了沒有」的判準在提問的人手上，所以那一類錯誤回的是一批形狀正確的列。

**第二支問「文字之外還有誰在決定」。** 各方決定的東西不同：**識別字規則**決定名字指向哪個物件、**權限系統**決定送出這段 SQL 的人被允許做什麼、**最佳化器**決定要花多久、**約束**決定資料能長成什麼樣、**collation** 決定兩個字串算不算相等。**引擎的寬鬆度與設定**在這幾方裡的位置不同——它決定的是其餘各方各自的線畫在哪裡，包含它接不接受一個不合標準的寫法（[1.19](/sql/engine-leniency-and-portability/)）。最佳化器是其中唯一不改變結果的，它受一條限制：輸出的列集合要與語意模型算出來的一致。約束介入的時機與其餘各方不同——它在這段查詢寫下來以前，就決定了它會遇到哪幾種列。

**第三支問「這段文字給人讀的那一面」。** 宣告式語言把要什麼結果寫成文字，於是同一段文字有兩個讀者：引擎讀行為，人讀宣告。[1.20](/sql/declared-intent-vs-behaviour/) 問文字說了什麼——選了 `LEFT` 就是宣告預期有配不到的列，而引擎從不查證這件事，宣告落空時查詢仍然回正確答案，代價落在下一個相信那段文字的人身上。[1.21](/sql/readable-and-fast-mostly-align/) 問文字該為誰而寫——兩個讀者的需求在 SQL 上多數時候指向同一個寫法，而分岔發生時出口在 schema 那一層。

前兩支的答案方向相反而問的是同一個性質的兩面，所以它們不是互斥的分類：第二方的實例就住在第一支的 [1.2](/sql/clause-evaluation-order/) 與 [1.9](/sql/grouping-key-decides-the-unit/) 裡（同一個寫法 SQLite 接受而 DuckDB 與 MySQL 拒絕）。[1.1](/sql/declarative-not-procedural/) 是分岔點——它把書寫順序、求值順序與執行順序分開，前兩者屬第一支，第三者屬第二支。

**用第二支之前要先讀得出手上這個資料庫的現況**，而查法不在查詢語言裡：名字實際存成什麼查系統目錄——資料庫把自己有哪些表、哪些欄位也存成表，那幾張就是系統目錄（`pg_tables` / `sqlite_master`）、自己有哪些授權查 `information_schema.role_table_grants`、有哪些索引查 `pg_indexes` 或 `PRAGMA index_list`、有沒有統計查 `pg_stats` 或 `sqlite_stat1`、哪些約束真的生效了查 `information_schema.table_constraints` 或 `PRAGMA foreign_key_list`、字串套哪一條比較規則查 `pg_database.datcollate`、`@@collation_database` 或 `PRAGMA collation_list`。

## 章節

### 第一支：語意的模型

| 篇                                                                                  | 交付                                                                |
| ----------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| [1.1 宣告式的紅利與代價](/sql/declarative-not-procedural/)                          | 三種順序各由誰決定，以及前兩支從哪裡分開                            |
| [1.2 子句的求值順序](/sql/clause-evaluation-order/)                                 | 每一步手上有什麼，以及哪些限制擋得掉哪些擋不掉                      |
| [1.3 連接從說出配對關係開始](/sql/join-starts-from-the-relationship/)               | 兩種起手式各把條件放在哪裡，以及連接的種類由什麼決定                |
| [1.4 JOIN 的左邊是累積結果](/sql/join-left-operand-accumulates/)                    | 鏈式 JOIN 的左運算元是什麼，RIGHT 在鏈裡保護了誰                    |
| [1.5 ON 描述關係、WHERE 篩選結果](/sql/on-describes-where-filters/)                 | 同一條件放兩處在內連接下同值而在外連接下不同值的原因                |
| [1.6 連接產出的是新的關係](/sql/join-changes-rows-and-nulls/)                       | 列數膨脹怎麼讓聚合算錯，以及 NULL 為什麼不能用等號比                |
| [1.7 查詢裡的表是一個具名的出現](/sql/table-occurrence-and-alias/)                  | 自連接需要別名的原因，以及什麼問題非它不可                          |
| [1.8 IN、EXISTS 與 JOIN](/sql/in-exists-join/)                                      | 三者在列數上的差別，以及選哪一種只問一句話                          |
| [1.9 分組鍵決定每一組代表什麼](/sql/grouping-key-decides-the-unit/)                 | 選鍵的判準，以及先問這一題需不需要分組                              |
| [1.10 分組把列收掉，視窗函數把列留著](/sql/window-keeps-rows-grouping-collapses/)   | 兩者的輸出單位差在哪，以及取相鄰列時的邊界                          |
| [1.11 關係沒有順序，只有 ORDER BY 加得回來](/sql/relations-have-no-order/)          | 順序跟著計畫走的機制、ORDER BY 在求值順序的位置，以及空值落在哪一端 |
| [1.12 分頁要一個全序](/sql/pagination-needs-a-total-order/)                         | 同分的列在分頁時重複與遺漏的機制，以及位置式與值式兩種游標          |
| [1.13 合不合法由引擎驗，答案對不對由提問的人負責](/sql/well-formed-is-not-correct/) | 正確性的兩層各由誰負責，以及答案錯掉時為什麼不報錯                  |

### 第二支：文字之外還有誰在決定

| 篇                                                                                            | 交付                                                                             |
| --------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| [1.14 識別字送進引擎之後會被改寫](/sql/identifier-rules/)                                     | 大小寫摺疊與引號各家的規則，以及混用時失效的時機                                 |
| [1.15 字串的相等、大小與索引可用性都由 collation 決定](/sql/string-comparison-and-collation/) | 同一條規則作用在相等、LIKE、排序與索引四個表面，以及它該寫在哪一層               |
| [1.16 權限的預設是什麼都不給](/sql/privilege-model/)                                          | 角色與 GRANT 的模型，以及最小權限在事故時省下什麼                                |
| [1.17 代價由資料與索引決定](/sql/cost-lives-in-the-plan/)                                     | 一道題三種寫法的實測，加一個索引之後排名對調                                     |
| [1.18 外鍵寫下保證，各家引擎決定它生不生效](/sql/foreign-key-and-referential-integrity/)      | 參照完整性擋下哪些寫入，以及宣告與生效在哪幾個位置分開                           |
| [1.19 哪一家最寬鬆只答得了一條軸，可攜性要逐條決定](/sql/engine-leniency-and-portability/)    | 五條寫法在四家上的分割互不預測，差異在什麼位置發聲分四級，以及可攜性維持到哪一級 |

### 第三支：文字對讀的人說了什麼

| 篇                                                                            | 交付                                       |
| ----------------------------------------------------------------------------- | ------------------------------------------ |
| [1.20 關鍵字宣告意圖，引擎只執行行為](/sql/declared-intent-vs-behaviour/)     | 宣告落空的幾種形態，以及查證宣告的那個動作 |
| [1.21 好讀的寫法多數時候也是引擎好走的](/sql/readable-and-fast-mostly-align/) | 兩者同向與分岔的量測，以及分岔時該動哪一層 |

**編號動過的時候要掃三個地方。** 章節的編號是它在序列裡的位置，插入或搬動一篇會讓引用它的每一處失準，而失準的引用不會報錯——連結仍然解析得到，只是文字上的編號指向別人。掃描的作用域是整個 `content/`，不是只有本分類——上一次重新編號漏掉的正是分類之外的一處引用。掃法要比對而不是列舉：把每篇 frontmatter 的編號當成正確答案，逐條檢查「連結文字裡的編號」與「它指向的 slug 現在的編號」對不對得上。抓連結的樣式是 `rg -n "\[[^]]*[0-9]\.[0-9]+[^]]*\]\(/sql/" content`——**數字未必緊接在 `[` 之後**，上一次與這一次漏掉的都是連結文字前綴了「SQL 」的那一條，而以 `\[1\.` 起手的樣式對它恆為零命中。另外用篇名反查一次補上不帶編號的：`rg -l "/sql/" content --glob '!content/sql/**'`。本頁除了三張章節表，帶編號的還有開場導引、三支敘述、問題落點表、跨分類引用與 Backlog，一律照同一條指令掃過。

## 帶著問題來的話，這張表給落點

上面那三支是讀完整個分類會走的順序。帶著一個具體問題進來的人不必照順序讀——多數篇的篇名是語法或語法結構，而手上的東西通常是一個業務問題，這張表把問題對到落點。

| 手上的問題                                                   | 去哪一篇                                                                                                                                                                                                                                       |
| ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 找出「沒有對應資料」的那些人或事                             | [1.9](/sql/grouping-key-decides-the-unit/)：從業務事實推到 `NOT EXISTS`，並說明為什麼計數那條路走不通                                                                                                                                          |
| 判斷「有沒有對應資料」，三種寫法選哪一個                     | [1.8](/sql/in-exists-join/)：三者在列數上的差別，選哪一種只問一句話                                                                                                                                                                            |
| 讀到 semi-join 或 anti-join，想知道它們指哪個運算            | [Semi-join 與 Anti-join（半連接與反連接）](/sql/knowledge-cards/semi-join-and-anti-join/)：`EXISTS` 與 `NOT EXISTS` 在代數裡的名字，以及列數上限為什麼是左邊那張表的列數                                                                       |
| 分組之後結果少了幾筆                                         | [1.9](/sql/grouping-key-decides-the-unit/)：分組鍵決定一組代表誰                                                                                                                                                                               |
| 連接之後數量變多、總和比預期大                               | [1.6](/sql/join-changes-rows-and-nulls/)：一列配到多列就複製一次                                                                                                                                                                               |
| 條件寫了卻回零列，而且沒有報錯                               | [1.6](/sql/join-changes-rows-and-nulls/)：空值的比較是第三種答案；零列也可能是問錯了問題，兩者的分法在 [1.13](/sql/well-formed-is-not-correct/)                                                                                                |
| 查出來的筆數比預期少，而且沒有報錯                           | 照順序排除三件事：`WHERE` 有沒有抵銷外連接的保護（[1.5](/sql/on-describes-where-filters/)）、比較或連接用的那一欄有沒有 `NULL`（[1.6](/sql/join-changes-rows-and-nulls/)）、兩者皆非就是問錯了問題（[1.13](/sql/well-formed-is-not-correct/)） |
| 想事先知道某個連接會不會掉列，不想每次都去翻資料             | [1.18](/sql/foreign-key-and-referential-integrity/)：答案由 schema 上的約束給，而那條宣告要先生效；五種約束各買到什麼在 [Constraint（約束）](/sql/knowledge-cards/constraint/)                                                                 |
| 分頁的時候同一筆資料出現在兩頁上、或有一筆從來沒出現過       | [1.12](/sql/pagination-needs-a-total-order/)：排序鍵不唯一時同分的列跟著計畫走，補一個唯一鍵、或把游標從位置換成值                                                                                                                             |
| 翻到後面的頁越來越慢                                         | [1.12](/sql/pagination-needs-a-total-order/) 的「OFFSET 的代價隨頁數往後而成長」一節：`OFFSET` 要先產出前面那些列再丟掉                                                                                                                        |
| 沒有寫 `ORDER BY`，而順序某天自己變了                        | [1.11](/sql/relations-have-no-order/)：關係是集合，順序是計畫剛好留下的形狀                                                                                                                                                                    |
| 同一段查詢換一個資料庫之後，比對名字或帳號的條件命中的列變了 | [1.15](/sql/string-comparison-and-collation/)：字串的相等由 collation 決定，各家預設不同                                                                                                                                                       |
| 建了索引，而 `LIKE 前綴%` 的查詢還是掃全表                   | [1.15](/sql/string-comparison-and-collation/) 的「索引的比較規則要跟條件的對得上」一節；條件形狀那一半在 [Sargable](/sql/knowledge-cards/sargable/)                                                                                            |
| 想知道最佳化器憑什麼決定要不要走索引                         | [Cardinality 與 Selectivity（基數與選擇率）](/sql/knowledge-cards/cardinality-and-selectivity/)：同一個索引對不同的值會有相反的決定                                                                                                            |
| 同一段查詢搬到另一家引擎，跑得動而答案不一樣                 | [1.19](/sql/engine-leniency-and-portability/)：四家的分組每一條都不同，而差異被發現的成本分四級                                                                                                                                                |
| 外連接寫了，加上條件之後該留的人不見了                       | [1.5](/sql/on-describes-where-filters/)：條件放 `ON` 還是 `WHERE`                                                                                                                                                                              |
| 好幾個 `JOIN` 疊起來，不確定某個 `LEFT` 保護了誰             | [1.4](/sql/join-left-operand-accumulates/)：左運算元是累積結果                                                                                                                                                                                 |
| 手上是一句業務描述，不知道連接該從哪裡下筆                   | [1.3](/sql/join-starts-from-the-relationship/) 的「從一句業務描述走到查詢」一節                                                                                                                                                                |
| 要拿同一批資料的兩列互相比較                                 | [1.7](/sql/table-occurrence-and-alias/)：表的一次出現與別名                                                                                                                                                                                    |
| 要在每一列旁邊放上它所屬那一組的總計或佔比                   | [1.10](/sql/window-keeps-rows-grouping-collapses/) 的「每一列與它所屬那一組的關係」一節                                                                                                                                                        |
| 拿每一列跟排在它前面那一列比，算出來的數字很怪               | [1.10](/sql/window-keeps-rows-grouping-collapses/) 的「相鄰的是什麼，要自己說清楚」一節                                                                                                                                                        |
| 查詢報錯說某個名字在這裡用不了                               | [1.2](/sql/clause-evaluation-order/)：每一步手上有什麼                                                                                                                                                                                         |
| 兩種寫法都對，想知道哪個代價低                               | [1.17](/sql/cost-lives-in-the-plan/)：代價由資料與索引決定                                                                                                                                                                                     |
| 查詢很慢，不知道從哪裡查起                                   | [1.17](/sql/cost-lives-in-the-plan/) 先問代價由什麼決定；條件的形狀是第一個要排除的，在 [Sargable](/sql/knowledge-cards/sargable/)                                                                                                             |
| 索引建了，計畫還是掃全表                                     | [Sargable（可走索引的條件形狀）](/sql/knowledge-cards/sargable/)：欄位被包住就走不了查找                                                                                                                                                       |
| 相關子查詢很慢，拆成 CTE 會不會比較好                        | [1.21](/sql/readable-and-fast-mostly-align/) 的「方向常常相反」一節：一整段的時間隨列數超線性成長而 CTE 接近線性                                                                                                                               |
| 查詢很難讀，想知道改成好讀的會不會變慢                       | [1.21](/sql/readable-and-fast-mostly-align/)：多數時候不用選，分岔時動 schema                                                                                                                                                                  |
| 沒有報錯，而查出來的結果跟預期對不上                         | [1.13](/sql/well-formed-is-not-correct/)：引擎驗的是合不合法                                                                                                                                                                                   |
| 想確認一段查詢問的是不是我要問的那一題                       | [1.13](/sql/well-formed-is-not-correct/) 的「判準只能來自查詢之外」一節                                                                                                                                                                        |
| 換一批資料之後，同一段查詢的答案就變了                       | [1.13](/sql/well-formed-is-not-correct/)：三種錯法各自要哪一筆資料才現形                                                                                                                                                                       |
| 查詢答案是對的，而寫法讀起來像在做另一件事                   | [1.20](/sql/declared-intent-vs-behaviour/)：宣告與行為分岔時怎麼查                                                                                                                                                                             |
| 要稽核別人寫的查詢，不知道從哪裡下手                         | [1.20](/sql/declared-intent-vs-behaviour/) 的「換掉關鍵字」一節：問這段文字說的話可不可信                                                                                                                                                      |
| 換一個資料庫之後找不到表                                     | [1.14](/sql/identifier-rules/)：識別字送進引擎會被改寫                                                                                                                                                                                         |
| 查詢回 `permission denied`                                   | [1.16](/sql/privilege-model/)：權限的預設是什麼都不給                                                                                                                                                                                          |
| 想知道引擎到底照什麼順序做事                                 | [1.1](/sql/declarative-not-procedural/)：三種順序各自由誰決定                                                                                                                                                                                  |

**選工具之前先把業務事實說成一句話。** 一句「沒消費過的顧客在訂單表裡不會有任何一列」就足以排除掉計數那一整條路——因為計數預設有東西可以數，而那些人一列都沒有。這一步在 [1.9](/sql/grouping-key-decides-the-unit/) 走了完整一遍。

## 各篇共用的範例資料庫

多數篇的查詢跑在同一組表上，一家小書店的三張表：顧客、訂單、評價。談代價與計畫的那幾篇需要大量資料，另外造自己的表並在篇內標明。

```sql
CREATE TABLE 顧客 (顧客編號 INT, 姓名 TEXT);
CREATE TABLE 訂單 (訂單編號 INT, 顧客編號 INT, 下單日 TEXT, 金額 INT);
CREATE TABLE 評價 (評價編號 INT, 訂單編號 INT, 星等 INT);

INSERT INTO 顧客 VALUES (1,'佳穎'), (2,'宗翰'), (3,'雅文');
INSERT INTO 訂單 VALUES (101,1,'2026-03-02',300), (102,1,'2026-03-09',500);
INSERT INTO 評價 VALUES (9001,101,5);
```

三個顧客裡只有佳穎下過單，她的兩張訂單裡只有第一張被評價過。**空缺是刻意留的**——外連接、NULL 與條件放哪裡的差別，全部要靠這些空缺才顯示得出來。

`RIGHT JOIN` 與 `FULL OUTER JOIN` 是後來才加進 SQLite 的，舊版回語法錯誤；遇到的話先用 `sqlite3 --version` 對一下手上這一份。

各篇的輸出都是實際跑出來的，多數在 SQLite 3.51 上。談權限的那一篇整篇在 PostgreSQL 18；比較各家行為的那幾篇另外用到 MySQL 8.4 與 DuckDB v0.10.3，牽涉到各家行為不同的地方都標明是哪一個引擎與哪一版。

**幾件跟版本有關的事。** 引擎的錯誤訊息會隨版本改措辭，所以各篇引的那些字串是對照用的，判讀看它拒絕了什麼、不看它怎麼說。各篇印出來的結果集為了對照固定了列序，而沒有 `ORDER BY` 的查詢實際回來的順序沒有保證（[1.11](/sql/relations-have-no-order/) 拿同一段查詢在建索引前後回不同順序示範這一條）。有幾篇會在共用資料上增刪幾列以顯示某個效果，那些改動只在該篇之內成立——換一篇之前回到上面這個初始狀態。

## 知識卡

語法元素的定義住在 [knowledge-cards](/sql/knowledge-cards/)。文章預設讀者已經知道那些詞指什麼，卡負責那一層。

## 這幾件事不住在這裡

資料庫工作的幾個主要議題已經有各自的落點，本分類不重寫它們——同一個主題兩套寫法會讓讀者拿到其中一套而不知道另一套存在。

- **資料表與欄位該怎麼取名**：[Schema Design 的「Naming 與一致性」段](/backend/01-database/schema-design/#naming-與一致性)給表、欄、外鍵、布林、時間戳、索引各自的慣例，以及縮寫不一致、隱性意義、跨表同義不同名這幾種反模式。本分類的 [1.14](/sql/identifier-rules/) 接在它後面，處理取好的名字送進引擎會被怎麼改寫。
- **資料庫怎麼設計**：同一篇的其餘各段給狀態責任的界定、索引設計、反正規化、分區策略與演進友好的結構。
- **資料層的攻擊面**：[攻擊者視角：資料層弱點判讀](/backend/01-database/red-team-data-layer/) 走注入、授權繞過、資料外洩、競態與資源耗盡五類，其中前三類各附真實事件對照，另有一段把失敗代價從資料外洩延伸到業務中斷。本分類的 [1.16](/sql/privilege-model/) 只處理其中「授權」這一層的語言機制。
- **遷移**：[資料庫轉換實作](/backend/01-database/database-migration-playbook/) 走雙寫、回填、切流與回滾；[Schema Migration Rollout 證據](/backend/01-database/schema-migration-rollout-evidence/) 走每一步要留下什麼證明。

## 跨分類引用

- → [backend 模組一 資料庫與持久化](/backend/01-database/)：查詢寫對之後的工程議題，交易邊界、遷移與每請求的查詢次數預算都在那裡
- → [PostgreSQL Query Optimization](/backend/01-database/vendors/postgresql/query-optimization/)：在真實系統上讀計畫要用的三層工具與四個 production case，本分類只到概念層
- → [Test Oracle（判斷標準來源）](/testing/knowledge-cards/test-oracle/)：一段查詢問對了沒有，判準從哪裡取得、各種取法各自抓不到什麼，在測試那一側有完整的分類；[1.13](/sql/well-formed-is-not-correct/) 只把它放回 SQL 的兩層裡講
- → [python 模組八 8.4 同一套關聯代數](/python/08-data-analysis/same-relational-algebra/)：同一組操作換成 DataFrame 介面的四組對應，以及對應斷掉的三個位置

## Backlog

| 項目                                           | 類型   | 前置條件                 | 規模 |
| ---------------------------------------------- | ------ | ------------------------ | ---- |
| 覆蓋索引                                       | 知識卡 | 無                       | 1    |
| 儲存引擎                                       | 知識卡 | 無                       | 1    |
| 系統目錄                                       | 知識卡 | 無                       | 1    |
| 「小表量不出計畫差異」收一個住址               | 跨模組 | 三處各自宣告的段落已存在 | 小   |
| 反向連結回補（backend / ddd / linux 共十餘處） | 跨模組 | 無                       | 中   |
| 約束改不改變執行計畫，在基線引擎上重驗         | 知識卡 | 已有一次異引擎量測       | 小   |

上一輪登記的四項——外鍵與參照完整性、`ORDER BY` 與分頁、字串值的大小寫、基數與選擇率——都已寫成篇或卡。

上表五項由一輪多輪審查的 outbound frame 抽出。三張卡的判定理由不同：**覆蓋索引**是 [1.12](/sql/pagination-needs-a-total-order/) 的 `OFFSET` 結論整條的承重詞而全站無卡；**儲存引擎**在 [1.18](/sql/foreign-key-and-referential-integrity/) 是讓宣告消失的第四條路，而本分類的卡系統已經用「引擎」指另一層，屬同域佔用而非單純缺卡；**系統目錄**被六個檔依賴，[1.19](/sql/engine-leniency-and-portability/) 第四級的整個判定靠它。

**約束改不改變執行計畫**這一條登記的是一次待驗的量測，而非一個已成立的結論。MySQL 8.0.46 上，`recordDate` 掛著唯一索引時最佳化器把 `EXISTS` 的[半連接](/sql/knowledge-cards/semi-join-and-anti-join/)降級成內連接——唯一性保證至多配到一列，去重的語意因此沒有作用。若同一個現象在 SQLite 與 DuckDB 上也成立，它就是 [1.17](/sql/cost-lives-in-the-plan/) 那條結論的第二個有界例外（第一個是 [Sargable](/sql/knowledge-cards/sargable/)），而兩個例外的性質不同：那裡是寫法擋住索引，這裡是 schema 上的宣告餵給最佳化器一條新資訊，也因此會界定 [Constraint](/sql/knowledge-cards/constraint/) 結尾「索引買的是查找速度，約束買的是內容的保證」那一句的邊界。本分類的實測基線是 SQLite 與 DuckDB，所以落點要等基線引擎上的計畫比對，不照抄異引擎的觀察。

「小表量不出計畫差異」這一條是缺住址而非缺內容：[1.15](/sql/string-comparison-and-collation/)、[1.12](/sql/pagination-needs-a-total-order/) 與[基數與選擇率](/sql/knowledge-cards/cardinality-and-selectivity/)各自就地宣告過一次，而它回答的問題比任何一篇的主題都早發生，落點在[執行計畫](/sql/knowledge-cards/query-plan/)或[最佳化器](/sql/knowledge-cards/query-optimizer/)那張卡。

另有兩處是**定義衝突而非缺口**，處置要動的是既有內容：[Query 反模式](/backend/01-database/query-anti-patterns/)的缺索引段把選擇率寫成欄位的屬性，而[基數與選擇率](/sql/knowledge-cards/cardinality-and-selectivity/)的第一句就是「選擇率是條件的屬性而非欄位的屬性」；[Database Engine](/sql/knowledge-cards/database-engine/) 的「四種決定」與本頁第二支的各方是兩套不對映的分解（卡按動作切、本頁按決定者切），缺的是一句說明兩者的軸不同。

### 後續候選

**從問題走到工具的判準怎麼排序**還沒決定要不要做，所以不建表登記——要看上面那張問題表用起來夠不夠，它本身已經是那個缺口的一種修法。

上一輪登記的「引擎的寬鬆度與可攜性之間的取捨」已寫成 [1.19](/sql/engine-leniency-and-portability/)。當時判斷要先確認的那件事（那些位置的形態分兩級、判讀成本差一個量級）在寫的過程中細分成四級，而分級的依據也換了——從「看不看得見」換成「要花多少工夫才知道有這件事」。
