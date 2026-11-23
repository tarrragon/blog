---
title: "1.21 資安、權限與合規決定的資料表設計：軟刪除與唯一約束、多租戶子表與列級安全性、RBAC 與非同步任務複查、存取憑證撤銷與優先序、個資分離與不可變稽核、角色預設權限與逾時護欄"
slug: "security-and-compliance-schema-decisions"
date: 2026-11-24
description: "建表與建模階段因應帳號生命週期、多租戶 RLS 隔離、背景任務授權、存取憑證撤銷、個資抹除合規與 PostgreSQL 角色預設權限（ALTER DEFAULT PRIVILEGES）及逾時護欄（statement_timeout／lock_timeout）所做的資料表選擇，各自對查詢正確性、索引效能與資料抹除帶來的代價、失效條件與事後遷移成本，附 SQLite 實測與 PostgreSQL 18 機制對照"
weight: 21
tags: ["backend", "database", "schema", "security", "rls", "rbac", "audit"]
---

這篇討論建表與資料建模階段因應資安、權限與個資合規邊界所做的結構決定：帳號表的軟刪除與唯一約束如何並存、多租戶架構下子表是否冗餘租戶鍵以及外連接與列級安全性（Row-Level Security，RLS）的互動、以角色為基礎的存取控制（Role-Based Access Control，RBAC）在多角色查詢與非同步背景任務上如何避免列數膨脹與越權、記錄登入狀態的工作階段（Session）與 API 金鑰的撤銷欄位設計及布林優先序邊界、個人識別資料（Personally Identifiable Information，PII）拆表加上受控檢視表如何化解唯附寫（append-only，僅允許新增、禁止修改與刪除）稽核與個資抹除的衝突，以及 PostgreSQL 角色層的預設權限與執行逾時設定。

閱讀本篇的前置背景是基本的關聯建模、SQL 查詢語意（`ON` 與 `WHERE` 的職責、`EXISTS` 與 `JOIN` 的列數差異、空值三值邏輯與索引），以及 [1.16 Schema 設計決定的查詢代價：可空性、排序鍵唯一性、表寬、一對多的切法、比較規則、外鍵執法，以及從另一張表取值時的複製與引用](/backend/01-database/design-decisions-price-every-query/) 所建立的思維——建表當下省略的約束與欄位，會轉化為往後每一次查詢都必須額外承擔的過濾條件、索引掃描或錯誤風險。效能與報表相關的設計疏漏造成延遲增加或報表數字誤差；資安與合規相關的設計疏漏則會導致跨租戶資料外洩、已撤銷的存取憑證（Credential）通過認證，或是不可變稽核與個資刪除等法規義務互相衝突。

本篇聚焦於資料表結構與查詢邊界，以下主題各自另有專篇涵蓋：

- **認證機制與存取憑證**：密碼雜湊演算法與工作因子見 [7.30 使用者密碼儲存：參數會過期的那一類原語](/backend/07-security-data-protection/password-storage-and-work-factor/)，認證方式選型見 [7.31 認證方式選型：可離線猜測的材料最後落在哪裡](/backend/07-security-data-protection/authentication-approach-selection/)，請求中攜帶存取憑證的協定選型見 [7.36 存取憑證在請求中怎麼帶：附上的決定由誰做](/backend/07-security-data-protection/credential-transport-in-request/)，登入節奏與多因子工作階段（Session）治理見 [7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)。
- **組織層資安治理與事故通報**：資料層整體攻擊面與紅隊弱點判讀見 [1.5 攻擊者視角（紅隊）：資料層弱點判讀](/backend/01-database/red-team-data-layer/)，組織層的資料分級與遮罩治理見 [7.4 資料保護與遮罩治理](/backend/07-security-data-protection/data-protection-and-masking-governance/)，高風險操作的稽核證據與責任切分見 [7.7 稽核追蹤與責任邊界](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/)，資料外洩後的對外通報流程見 [8.26 資料外洩時對商家的通知：外洩來源的歸屬判定、風險預警、確認與結案通知、調查報告](/backend/08-incident-response/security-incident-customer-notification/)。
- **資料庫權限基礎模型**：PostgreSQL `CREATE ROLE` 與 `GRANT` 的基礎授權模型見 [SQL.16 SQL 的權限模型：角色、GRANT 的授權單位與最小權限](/backend/01-database/sql/privilege-model/)。

文中的 SQLite 查詢與報錯輸出皆透過 Python `sqlite3` 模組於本機 SQLite 3.53.0 實際執行（查詢結果以 tuple 清單呈現）；PostgreSQL 18 的列級安全性（RLS）、預設權限與逾時參數行為取自 PostgreSQL 18 官方文件，未於本機執行。文中以「列（row）」指橫向的一筆資料、「欄（column）」指縱向的一個位置。

## 軟刪除對唯一約束與帳號查詢的連鎖代價

軟刪除（soft delete）是在資料列加上刪除時間戳欄位（例如 `deleted_at`），以標記取代實際執行 `DELETE`，目的是保留歷史訂單、排班或稽核紀錄指向這筆帳號的外鍵參照。當帳號表以軟刪除取代硬刪除之後，資料庫的唯一性保證與所有讀取帳號的查詢同時改變。

建表階段常須同時滿足互有張力的業務要求：保留已離職或已註銷的歷史帳號列、在任意時間點阻止兩筆生效中的帳號列帶有相同電子郵件信箱（含大小寫變體），同時允許離職復職或註銷後重新註冊同一個信箱。若直接在整張表宣告普通的 `UNIQUE(email)`，已標記 `deleted_at` 的歷史列仍然計入唯一鍵集合，復職重註冊會觸發唯一約束違規而寫入失敗，且預設區分大小寫的比較規則會將 `MGR@shop.example` 與 `mgr@shop.example` 判定為不同字串而允許兩者同時寫入。若為了遷就軟刪除而撤掉資料庫唯一約束、改由應用程式在寫入前先查再插，並行註冊請求就會在競態下寫出重複的生效信箱，引發帳號歸屬混淆。

解法是把唯一性約束的適用集合限縮到尚未刪除的列，也就是在資料庫建立附帶篩選條件的部分唯一索引（partial unique index，見 [Partial Index（部分索引）](/backend/knowledge-cards/partial-index/) 卡），並對信箱做小寫正規化（部分索引在 PostgreSQL 與 SQLite 支援；不支援部分索引的資料庫引擎如 MySQL，須另建產生欄搭配一般 `UNIQUE` 約束實現同等效果；正式建表同時使用 `status` 與 `deleted_at` 表達離職狀態時，亦建議補上表級 `CHECK ((status = 'offboarded') = (deleted_at IS NOT NULL))` 防止兩欄狀態漂移）：

```sql
-- SQLite 3.53.0（PostgreSQL 18 亦支援相同的表達式部分唯一索引語法，實務中 deleted_at 改採 TIMESTAMPTZ）
-- staff_id 為代理主鍵（surrogate key）；deleted_at 為 NULL 代表帳號仍存在於有效名單
CREATE TABLE staff_accounts (
  staff_id   INTEGER PRIMARY KEY,
  email      TEXT NOT NULL,
  status     TEXT NOT NULL CHECK (status IN ('active', 'suspended', 'offboarded')),
  deleted_at TEXT
);

CREATE UNIQUE INDEX uq_staff_active_email
  ON staff_accounts (LOWER(email))
  WHERE deleted_at IS NULL;

INSERT INTO staff_accounts VALUES
  (10, 'mgr@shop.example',    'active',     NULL),
  (13, 'ex.mgr@shop.example', 'offboarded', '2026-03-10 00:00:00');
```

這個部分唯一索引生效後，離職員工 13 復職時以大寫變體 `EX.MGR@shop.example` 建立新列會順利寫入，而針對在職員工 10 建立大小寫變體 `MGR@shop.example` 會立刻遭到資料庫引擎拒絕：

```sql
-- 復職重註冊（離職軟刪除信箱的大寫變體）：寫入通過
INSERT INTO staff_accounts VALUES (20, 'EX.MGR@shop.example', 'active', NULL);

-- 在職信箱變體寫入（與在職列 10 衝突）：遭部分唯一索引拒絕
INSERT INTO staff_accounts VALUES (21, 'MGR@shop.example', 'active', NULL);
```

```text
復職重註冊（staff_id = 20）：成功寫入，歷史離職列 13 維持原樣
在職信箱變體寫入（staff_id = 21）：UNIQUE constraint failed: index 'uq_staff_active_email'
```

部分唯一索引解決了寫入端的唯一性衝突，卻沒有消除軟刪除在讀取端衍生的安全風險。在硬刪除（hard delete）模型下，被刪除的帳號從資料表裡移除，任何登入或權限查詢都查不到這筆列；在軟刪除模型下，離職列 13 永久留在同一張表裡，開發者因此必須在全系統每一條讀取帳號的查詢裡各自補上過濾已刪除與已離職帳號的條件：

```sql
-- 漏寫 status 與 deleted_at 條件的登入查詢：同時回傳已離職列 13 與新列 20
SELECT staff_id, status
FROM staff_accounts
WHERE LOWER(email) = 'ex.mgr@shop.example'
ORDER BY staff_id;

-- 補齊狀態與軟刪除條件的查詢：僅回傳生效中的列 20
SELECT staff_id, status
FROM staff_accounts
WHERE LOWER(email) = 'ex.mgr@shop.example'
  AND status = 'active'
  AND deleted_at IS NULL;
```

```text
漏寫條件：[(13, 'offboarded'), (20, 'active')]
補齊條件：[(20, 'active')]
```

只要報表端點、密碼重設端點或舊版管理腳本裡有一條查詢沒有加上 `deleted_at IS NULL` 與 `status = 'active'`，已離職帳號仍可通過該路徑的驗證或查詢。這類查詢缺漏在系統剛上線、表裡還沒有軟刪除資料時不會觸發任何錯誤，直到第一位員工離職、該條未過濾的查詢實際執行後才會顯現。

當業務要求帳號表保留歷史外鍵參照、又允許原信箱重新註冊時，在帳號表使用軟刪除搭配 `WHERE deleted_at IS NULL` 的部分唯一索引可同時滿足參照完整與寫入唯一；代價是開發者必須在每一條業務查詢裡補上 `status = 'active'` 與 `deleted_at IS NULL` 條件，只要任一條查詢遺漏就會回傳離職帳號（在 PostgreSQL 上可另建僅包含生效列並加上 `WITH (security_barrier = true)` 的檢視表（view）供日常服務讀取，防止呼叫端外層非 `LEAKPROOF` 條件被查詢最佳化器下推並藉由錯誤副作用側錄已被過濾的離職列，並將全表查詢限縮給稽核角色）。

若系統不允許同信箱重複使用，可沿用整表 `UNIQUE(LOWER(email))` 而不必建部分唯一索引，但只要仍採軟刪除保留歷史外鍵，讀取查詢仍須過濾 `deleted_at IS NULL` 與 `status = 'active'`；唯有改採硬刪除或將離職帳號移至獨立歷史歸檔表，才能消除主表裡的軟刪除殘留列。如果帳號表同時受個資抹除約束、須在離職或註銷後清空明文信箱，建表時應將主表 `email` 改為可空並補上 `CHECK (deleted_at IS NOT NULL OR email IS NOT NULL)`，抹除離職列時再把 `email` 更新為 `NULL`（或不可逆匿名佔位字串），或者把 `email` 與 `deleted_at` 共同移入獨立的可抹除帳號憑證表，以維持單表部分唯一索引。關於刪除帳號後公開名稱或識別碼的回收與保留，可延伸看 [10.6 命名空間與網域的處置：續約、名稱保留與回收、懸空 DNS](/backend/10-system-evolution/namespace-and-domain-disposition/) 的〈名稱的保留與回收：套件名稱、雲端資源名稱與短碼〉。

## 多租戶子表的租戶鍵、外連接洩漏與 PostgreSQL RLS 邊界

在多租戶共用資料表（pool 模式，各層隔離模型比較見 [7.44 多租戶平台的隔離層級：資料存放、建置管線、營運後台、資料庫管理與備份的權限範圍，跨租戶資料整合，以及事故報告要交代的隔離資訊](/backend/07-security-data-protection/multi-tenant-platform-isolation-tiers/)）架構下，不同客戶的資料存放於同一組資料表，並以租戶鍵（例如 `merchant_id`）區分資料歸屬。建表時常只在父表（如運單表 `shipments`）放置租戶鍵，子表（如包裹表 `shipment_packages`）只放外鍵 `shipment_id`。這個決定同時影響多表查詢的語意邊界與資料庫層列級安全性的索引成本。

在多表查詢的語意邊界上，開發者有時會在子表查詢裡使用 `LEFT JOIN` 接父表（例如預期可能存在缺少父紀錄的匯入資料），並把租戶條件寫進 `ON` 子句。[SQL.5 ON 與 WHERE：連接條件與篩選條件各自的職責](/backend/01-database/sql/on-describes-where-filters/) 已經推導過：`LEFT JOIN` 會保留左表的所有列，寫進 `ON` 的右表條件只決定右表列是否符合連接條件（不符時右表欄位補 `NULL`），不會濾除左表列。在單租戶報表裡，這個錯誤只會讓報表多出幾筆金額為零的列；在多租戶查詢裡，它會直接把全平台其他租戶的子表資料全部回傳給目前登入的單一租戶：

```sql
-- SQLite 3.53.0
-- 商家 1001 有兩件包裹（7101、7102）、商家 1002 有一件（7105）、商家 1004 有一件（7108）
-- 子表此處先放入 NOT NULL 的 merchant_id，供並排示範 LEFT JOIN 外洩與子表租戶鍵過濾
CREATE TABLE shipments (
  shipment_id INTEGER PRIMARY KEY,
  merchant_id INTEGER NOT NULL,
  status      TEXT NOT NULL
);
CREATE TABLE shipment_packages (
  package_id   INTEGER PRIMARY KEY,
  shipment_id  INTEGER NOT NULL REFERENCES shipments(shipment_id),
  merchant_id  INTEGER NOT NULL,
  weight_grams INTEGER NOT NULL
);

INSERT INTO shipments VALUES
  (7001, 1001, 'delivered'),
  (7004, 1002, 'created'),
  (7007, 1004, 'in_transit');
INSERT INTO shipment_packages VALUES
  (7101, 7001, 1001, 1200),
  (7102, 7001, 1001, 2400),
  (7105, 7004, 1002, 500),
  (7108, 7007, 1004, 2200);

-- 錯誤寫法（LEFT JOIN ... ON）：左表所有商家的包裹全部外洩，僅非 1002 的右表狀態補 NULL
SELECT p.package_id, p.weight_grams, s.status
FROM shipment_packages p
LEFT JOIN shipments s
  ON p.shipment_id = s.shipment_id AND s.merchant_id = 1002
ORDER BY p.package_id;

-- 正確寫法（INNER JOIN + 租戶條件）：僅回傳商家 1002 的包裹
SELECT p.package_id, p.weight_grams, s.status
FROM shipment_packages p
INNER JOIN shipments s
  ON p.shipment_id = s.shipment_id AND p.merchant_id = s.merchant_id
WHERE p.merchant_id = 1002
ORDER BY p.package_id;
```

```text
LEFT JOIN ... ON 寫法：
[(7101, 1200, None), (7102, 2400, None), (7105, 500, 'created'), (7108, 2200, None)]

INNER JOIN + 租戶條件寫法：
[(7105, 500, 'created')]
```

授權邊界的查詢屬於失敗即關閉（fail-closed）的集合過濾：任何找不到父紀錄或租戶不符的列都必須被排除，而不是以 `LEFT JOIN` 或 `OR s.shipment_id IS NULL` 保留下來。

在導入 PostgreSQL 列級安全性（RLS）作為縱深防禦（defense in depth）時，子表是否冗餘租戶鍵直接決定查詢計畫的成本。RLS 讓資料庫引擎對受政策約束角色的查詢依連線變數自動補上過濾條件，避免開發者在應用程式查詢裡漏寫 `WHERE merchant_id = ...` 時回傳其他租戶資料（嵌入式與伺服器端資料庫在角色身分與連線協調上的部署形態差異見 [SQL.20 引擎的部署形態與 SQL 構造：SQLite 與 PostgreSQL 在並行寫入、連線協調與身分上的差異](/backend/01-database/sql/deployment-shape-and-sql-constructs/)）。如果子表沒有冗餘 `merchant_id`，子表的 RLS 政策就只能寫成跨表 `EXISTS (SELECT 1 FROM shipments s WHERE s.shipment_id = shipment_packages.shipment_id AND s.merchant_id = ...)`。由於子表缺乏租戶鍵，查詢最佳化器每次掃描子表都必須執行跨表檢查；當子表列數大、無法單靠子表索引濾除其他租戶列而須逐列回查父表時，原本用來限制租戶資料範圍的 RLS 政策反而會引發大量掃描與連線延遲。

要讓子表 RLS 直接命中單表索引並在資料庫層保證父子表租戶一致，建模時須由父表與子表各自建立對應約束：父表 `shipments` 須宣告 `UNIQUE (merchant_id, shipment_id)`（或直接設為複合主鍵），因為 PostgreSQL 要求複合外鍵的被參照端具備對應唯一約束或非部分唯一索引；子表則冗餘 `NOT NULL` 的 `merchant_id` 欄位並建立複合索引 `(merchant_id, shipment_id)`，再宣告複合外鍵 `FOREIGN KEY (merchant_id, shipment_id) REFERENCES shipments(merchant_id, shipment_id)` 指向父表的唯一約束。此處子表的 `merchant_id` 不可允許 `NULL`，否則在 SQL 預設的 `MATCH SIMPLE` 規則下，只要複合外鍵任一欄為 `NULL`，資料庫引擎就會直接略過外鍵檢查。若父表已按時間範圍分割（例如依 `created_at` 分割，見 [1.19 資料表長期成長的成本：查詢讀的量、列表的部分索引、查詢以外的成本、分割與唯一約束、批次資料的共用欄位](/backend/01-database/table-growth-query-cost/)），PostgreSQL 要求分割表的所有唯一約束都須包含分割鍵，無法建立純 `(merchant_id, shipment_id)` 唯一約束，此時須把分割鍵納入複合鍵或改由應用與觸發器維持父子租戶一致。反之，若子表規模小、沒有啟用資料庫層 RLS 的需求，且所有子表查詢都強制經由父表主鍵關聯，不冗餘租戶鍵可省去父表複合唯一索引與寫入一致性維護成本。

PostgreSQL 18 啟用 RLS 時另有幾項容易靜默失效的設定邊界（依 PostgreSQL 18 官方文件〈Row Security Policies〉、〈pg_dump〉與〈SET〉，未於本機實跑）：

- **`FORCE ROW LEVEL SECURITY` 與 `NOBYPASSRLS`**：對資料表執行 `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` 後，RLS 政策預設不對資料表擁有者（table owner）生效，也不對 `SUPERUSER` 或具有 `BYPASSRLS` 屬性的角色生效（`CREATE ROLE` 建立一般角色時預設即為 `NOBYPASSRLS`，顯式寫出屬於防禦性宣告）。表擁有者預設豁免的效果，是擁有者執行結構遷移、備份或管理查詢時可讀取全表資料、不受業務租戶政策過濾（從機制推論；PostgreSQL 18〈Row Security Policies〉未明寫設計意圖）。當應用程式誤用表擁有者帳號連線時，資料庫引擎不會套用任何 RLS 政策；管理員加上 `ALTER TABLE ... FORCE ROW LEVEL SECURITY` 後，資料庫會取消非 `BYPASSRLS` 表擁有者的預設豁免，但對 `SUPERUSER` 與 `BYPASSRLS` 角色依然無效。
- **`FORCE RLS` 對回填腳本與 `pg_dump` 的不同副作用**：啟用 `FORCE` 後，屬 `NOBYPASSRLS` 的表擁有者（例如遷移帳號）會面臨兩種不同失效形態。一般資料回填腳本在預設 `row_security = on` 下，若政策只授與應用角色，擁有者會命中預設拒絕而靜默讀不到任何列（可改用 `BYPASSRLS` 角色或補上對應政策）；`pg_dump` 預設則會執行 `SET row_security = off`，只要角色受至少一條 RLS 政策影響就會直接報錯中止（`query would be affected by row-level security policy`），即使替該角色補上 `USING (true)` 政策依然失敗。因此備份須規劃具 `BYPASSRLS`（或 `SUPERUSER`）的專用角色，或顯式傳入 `--enable-row-security`（但只會匯出該角色政策可見的子集）。
- **寫入端 `WITH CHECK` 與認證前查表的例外邊界**：RLS 政策同時涵蓋讀取篩選（`USING`）與寫入檢核（`WITH CHECK`，防止連線寫入不屬於當前租戶的 `merchant_id`）。此外，系統在認證階段尚未取得 `merchant_id` 之前（例如登入或依 API 金鑰雜湊反查所屬租戶），不可對憑證表直接套用依賴 `app.current_merchant_id` 的 `FORCE RLS`，否則認證查詢會因尚未設定租戶變數而陷入死鎖；這類反查須另設限定的認證查詢函式或獨立政策。受控跨租戶的客服或風控查詢亦應透過帶審計條件的獨立政策授權，避免直接授與全庫 `BYPASSRLS`。
- **交易內 `SET LOCAL` 與連線池隔離**：在 PostgreSQL 裡執行 `SET` 且省略作用域關鍵字時，預設作用域為 `SESSION`（整條連線持續生效）。`SET SESSION` 的效果是應用程式使用未經連線池共用的專屬長連線時，多筆交易可沿用同一組執行期設定（例如時區、`search_path` 或固定身分），不必每筆交易重設（從機制推論；PostgreSQL 18〈SET〉未明寫設計意圖）。當系統透過外部連線池代理器 PgBouncer（須運作於交易級連線池（Transaction Pooling）或 `session` 池模式；`statement` 模式禁止多語句交易）或應用程式連線池重複使用連線時，若使用連線層級的 `SET app.current_merchant_id = '1002'`（`app.` 是 PostgreSQL 自訂執行期參數要求的命名空間前綴，可替換為專案前綴但不可省略句點；`'1002'` 為示範商家編號且自訂參數一律以字串存放），底層連線歸還連線池後變數仍會留存；若應用程式處理下一筆請求時未重新設定該參數，查詢就會沿用前一個商家的租戶身分。
- **`SET LOCAL` 的交易邊界與空字串重設**：改在明確交易區塊（`BEGIN ... COMMIT`）內執行 `SET LOCAL` 後，PostgreSQL 會在交易結束時清除該設定（於自動提交模式下執行 `SET LOCAL` 會觸發警告且不影響下一句）。此外，自訂參數經 `SET LOCAL` 註冊後，交易結束時 PostgreSQL 會將其值重設為空字串 `''` 而非 `NULL`。當團隊需要漏設租戶上下文時靜默回傳 0 列、避免型別轉換錯誤中斷查詢，RLS 政策轉型整數可寫為 `NULLIF(current_setting('app.current_merchant_id', true), '')::integer`；反之，若要求任何漏設租戶變數的請求當場報錯（fail-loud）以暴露中介層缺漏，則刻意不包 `NULLIF`（或省略第二參數 `true`），讓空字串直接觸發報錯。
- **索引前導欄位對齊 RLS 條件**：開啟 RLS 後，對於受 RLS 政策約束的角色，每一條查詢都會被資料庫改寫加上 `merchant_id = ...`。若高頻查詢對應的複合索引未將 `merchant_id` 設為前導或合適位置，索引效益會大幅下降（複合索引欄位順序原則見 [1.2 Schema Design 與資料建模](/backend/01-database/schema-design/) 的〈Index 設計〉；篩選欄位未納入索引時隨表成長的掃描量實測見 [1.19 資料表長期成長的成本：查詢讀的量、列表的部分索引、查詢以外的成本、分割與唯一約束、批次資料的共用欄位](/backend/01-database/table-growth-query-cost/)）。

## RBAC 多角色查詢與非同步任務的困惑代理人

當團隊導入以角色為基礎的存取控制（RBAC，由帳號表、角色指派表與角色權限表組成多對多關係；正式系統通常會把角色與權限主檔另拆成 `roles` 與 `permissions`），並且由背景工作程序（worker）替使用者非同步執行高權限操作（例如批次匯出訂單報表）時，資料表建模與查詢設計必須同時處理時間差權限逃逸與多對多連接列數膨脹兩類失效形態。

時間差權限逃逸在資安領域稱為困惑代理人（Confused Deputy）：使用者在排入任務當下具有合法權限，背景 worker 則以高權限資料庫角色在數分鐘或數小時後實際讀取資料並產檔。如果 worker 只認領 `export_jobs.status = 'queued'`，沒有在執行前複查請求者當下的帳號狀態與角色有效期，已離職或已被撤權的人就能透過預先排入的任務讓 worker 代為輸出機密報表。另一個常見的建模疏漏是離職處理程式只將 `staff_accounts.status` 更新為 `'offboarded'` 並寫入 `deleted_at`，未同步更新 `staff_roles.revoked_at`——此時如果 worker 只查 `staff_roles` 而不回查 `staff_accounts`，依然會放行離職者的任務。

即使開發者記得把帳號、角色指派與角色權限表都聯查進來，把權限表直接以 `INNER JOIN` 接在主查詢後面還會觸發多對多連接的列數膨脹缺陷。同一個員工同時身兼多個角色（例如 `store_manager` 與 `auditor`），而這些角色都包含 `orders:export` 權限時，`JOIN` 運算會將同一筆匯出任務展開成多筆結果列（連接造成列數膨脹的機制見 [SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)，`IN`、`EXISTS` 與 `JOIN` 在列數與空值上的差異見 [SQL.8 IN、EXISTS 與 JOIN：列數、可取用的欄位與 NULL 的處理](/backend/01-database/sql/in-exists-join/)）。以下在 SQLite 3.53.0 實跑對照未複查請求者、直接 `JOIN` 與 `EXISTS` 半連接的結果差異：

```sql
-- SQLite 3.53.0（簡化為三張 RBAC 表；正式環境常另拆 roles 與 permissions 主檔）
-- 員工 10 在職且同時具 store_manager 與 auditor（皆有 orders:export），發起任務 504
-- 員工 13 已離職軟刪除，但 staff_roles 漏填 revoked_at，發起任務 505
-- store_scope 為 NULL 在本範例代表全域角色（如總部 auditor），不同建模約定的安全邊界見下方正文
-- '2026-03-20 03:05:00' 為示範用的 worker 執行當下時間，實務應換為當下時間參數或 CURRENT_TIMESTAMP
CREATE TABLE staff_accounts (staff_id INTEGER PRIMARY KEY, status TEXT NOT NULL, deleted_at TEXT);
CREATE TABLE staff_roles (staff_id INTEGER, role_code TEXT, store_scope TEXT, revoked_at TEXT, expires_at TEXT);
CREATE TABLE role_permissions (role_code TEXT, perm_code TEXT);
CREATE TABLE export_jobs (job_id INTEGER PRIMARY KEY, status TEXT NOT NULL, requested_by INTEGER NOT NULL, scope_store TEXT);

INSERT INTO staff_accounts VALUES (10, 'active', NULL), (13, 'offboarded', '2026-03-10 00:00:00');
INSERT INTO role_permissions VALUES ('store_manager', 'orders:export'), ('auditor', 'orders:export');
INSERT INTO staff_roles VALUES
  (10, 'store_manager', 'TPE-01', NULL, NULL),
  (10, 'auditor',       NULL,     NULL, NULL),
  (13, 'store_manager', 'TPE-01', NULL, NULL);
INSERT INTO export_jobs VALUES (504, 'queued', 10, 'TPE-01'), (505, 'queued', 13, 'TPE-01');

-- 未複查請求者：直接認領 queued 任務
SELECT job_id FROM export_jobs WHERE status = 'queued' ORDER BY job_id;

-- 直接 JOIN RBAC 表：多角色重疊權限造成任務 504 膨脹為兩列
SELECT j.job_id
FROM export_jobs j
JOIN staff_accounts sa ON sa.staff_id = j.requested_by
JOIN staff_roles sr ON sr.staff_id = sa.staff_id
JOIN role_permissions rp ON rp.role_code = sr.role_code
WHERE j.status = 'queued'
  AND sa.status = 'active' AND sa.deleted_at IS NULL
  AND sr.revoked_at IS NULL AND rp.perm_code = 'orders:export'
ORDER BY j.job_id;

-- EXISTS 半連接：同時驗證主帳號、撤銷、過期與門市範圍，且列數上限固定受限於任務表
SELECT j.job_id
FROM export_jobs j
WHERE j.status = 'queued'
  AND EXISTS (
    SELECT 1
    FROM staff_accounts sa
    JOIN staff_roles sr ON sr.staff_id = sa.staff_id
    JOIN role_permissions rp ON rp.role_code = sr.role_code
    WHERE sa.staff_id = j.requested_by
      AND sa.status = 'active' AND sa.deleted_at IS NULL
      AND sr.revoked_at IS NULL
      AND (sr.expires_at IS NULL OR sr.expires_at > '2026-03-20 03:05:00')
      AND rp.perm_code = 'orders:export'
      AND (sr.store_scope IS NULL OR sr.store_scope = j.scope_store)
  )
ORDER BY j.job_id;
```

```text
未複查請求者：[(504,), (505,)]   -- 誤幫離職者 13 執行匯出
直接 JOIN RBAC：[(504,), (504,)] -- 雙角色重疊權限造成任務列數膨脹
EXISTS 半連接：[(504,)]          -- 攔下 505、且 504 保持單列
```

權限判斷驗證的是存在性條件：這位請求者當下是否具備至少一條未撤銷、未過期且涵蓋目標資源範圍的有效授權路徑。以半連接（semi-join，即 `EXISTS`，見 [Semi-join 與 Anti-join（半連接與反連接）](/backend/01-database/sql/knowledge-cards/semi-join-and-anti-join/) 卡）表達這項存在性條件時，結果集的列數上限固定受限於外層任務表，不會因使用者擁有多少個重疊角色而膨脹；同時建表階段為 `export_jobs` 補齊請求者識別欄位（`requested_by`）與作用範圍欄位（`scope_store`），非同步 worker 才有辦法在實際執行當下落實權限複查。

實務落地時不可只靠 `SELECT ... WHERE status = 'queued' AND EXISTS (...)` 略過未通過複查的任務：被略過的列（例如離職員工 13 的任務 505）會永久滯留在 `queued` 狀態，造成每次輪詢重複掃描；若帳號因疑似遭盜用被設為 `suspended`、日後清查復權改回 `active`，停權前排入的舊任務還會在無人重送下自動復活並執行。worker 應先鎖定候選任務（多 worker 併發時搭配 `FOR UPDATE SKIP LOCKED`）再檢查授權，未通過者寫入終止狀態（如 `denied` 或 `cancelled`）並記錄稽核原因，同時在帳號離職、停權或重設密碼當下同步撤銷該帳號尚在排隊中的任務。若背景任務由 API 金鑰或服務帳號而非人類員工發起，任務表須改存憑證與租戶識別並複查 `merchant_api_keys.revoked_at` 與 `merchants.status`；本節示範假設身分與任務同駐同一關聯式資料庫，若身分權限由外部身分提供者（IdP）或跨服務管理，則須另行處理停用同步與複查窗口（見 [7.38 外部身分與本地紀錄：兩條生命週期在哪裡分岔](/backend/07-security-data-protection/external-identity-local-record-lifecycle/)）。

作用範圍欄位 `store_scope` 是否允許 `NULL` 必須在建表當下約定單一語意：上述範例將 `store_scope IS NULL` 定義為「不限門市的全域角色（如總部 auditor）」，因此 `EXISTS` 查詢以 `sr.store_scope IS NULL OR sr.store_scope = j.scope_store` 放行；此外在 SQL 預設規則下 `NULL` 與 `NULL` 不視為相等，若對 `(staff_id, role_code, store_scope)` 建立一般唯一約束，會允許同一員工重複指派多筆 `store_scope IS NULL` 的全域角色（PostgreSQL 15 起須改用 `UNIQUE NULLS NOT DISTINCT` 或部分唯一索引）。反之，若系統的資料模型將 `NULL` 定義為「尚未指派門市（無權限）」，沿用 `IS NULL` 條件就會把未指派門市的帳號誤判為全域授權而放行，建模時應改用顯式布林欄位（如 `is_global` 並搭配互斥檢查 `CHECK ((is_global AND store_scope IS NULL) OR (NOT is_global AND store_scope IS NOT NULL))`）或專用範圍識別值區分兩者。若系統沒有非同步高權限作業且採用單一角色欄位（一對一而非多對多），則不需要 `EXISTS` 防止列數膨脹，但查詢仍須核對主帳號狀態與軟刪除欄位。

## 存取憑證、Session 與 API 金鑰的撤銷模型與布林優先序

針對登入 Session 表與 API 金鑰表的驗證查詢，在系統裡的呼叫頻率極高，同時也是最容易因為欄位缺漏或條件誤寫而出現認證繞過的位置。這類設計可拆成撤銷所需時間狀態欄位的建模，以及避免布林優先序與空值三值邏輯造成認證繞過的查詢邊界。

在 Session 模型裡，只存 `expires_at`（自然過期時間）與 `revoked_at`（主動登出時間）無法覆蓋所有即時撤銷情境。當帳號遭盜用、使用者緊急重設密碼，或安全團隊將帳號設為 `locked` 時，如果其中一條密碼重設程式路徑未執行批次更新 `user_sessions.revoked_at`，攻擊者手上的舊 Session 就會持續有效直到自然過期。把 `password_changed_at` 留在 `user_credentials` 並把帳號鎖定狀態留在 `users`，驗證查詢就能同時核對帳號啟用狀態、未軟刪除、Session 未撤銷且尚未過期，以及 Session 建立時間不早於最近一次密碼變更時間，形成即使某條程式路徑漏掉批次撤銷動作仍能即時攔截舊 Session 的資料層強制驗證邊界。時間戳比較須統一由資料庫時鐘寫入以避免跨節點應用時鐘偏移，並留意時間精度邊界（同秒內 `>=` 可能放行改密前同秒建立的舊 Session）；若系統包含僅用 Passkey 或 SSO 登入的無密碼帳號，或需要承載非改密碼觸發的全域登出（例如 IdP 撤權或重設多因子認證），則改在 `users` 維護 `sessions_valid_after`（或單調遞增的 `credential_version`）而非綁定於 `user_credentials.password_changed_at`。此外，高併發系統若改以 Redis 或短效 JWT 承載工作階段，則須在快取與權杖層另行處理撤銷同步窗口。

在 API 金鑰模型裡，資料表存放短前綴（`key_prefix`）供日誌辨識與初篩、把不可逆雜湊值（`key_hash`）設為 `UNIQUE` 供查表比對，不存放完整金鑰明文（直接以 `UNIQUE(key_hash)` 查表適用於高熵隨機金鑰搭配確定性雜湊如 SHA-256 或帶固定 pepper 的 HMAC-SHA256；若採逐列隨機鹽的慢雜湊則無法直接以雜湊值查表，須先以 `key_prefix` 定位候選列再於應用層驗證）；同時明確拆出權限範圍（`scopes`）、到期時間（`expires_at`，允許 `NULL` 代表未設到期日）與撤銷時間（`revoked_at`），並與所屬租戶表的 `status` 綁定。一旦查詢同時出現 `AND` 與 `OR`（判斷未設到期日或尚未到期），少了外層括號就會觸發語法合法的認證繞過——因為在 SQL 裡 `AND` 的運算優先序高於 `OR`。以下在 SQLite 3.53.0 實跑驗證 Session 密碼變更失效與 API 金鑰 `AND`/`OR` 優先序繞過：

```sql
-- SQLite 3.53.0（'2026-03-15 10:00:00' 為示範用當前驗證時間，實務換為當下時間參數）
-- 701 為改密碼前被盜舊 Session、702 為改密碼後合法 Session、703 已撤銷、704 帳號已鎖定
CREATE TABLE users (user_id INTEGER PRIMARY KEY, status TEXT NOT NULL, deleted_at TEXT);
CREATE TABLE user_credentials (user_id INTEGER PRIMARY KEY, password_changed_at TEXT NOT NULL);
CREATE TABLE user_sessions (session_id INTEGER PRIMARY KEY, user_id INTEGER, created_at TEXT, expires_at TEXT, revoked_at TEXT);

INSERT INTO users VALUES (1, 'active', NULL), (2, 'active', NULL), (4, 'locked', NULL);
INSERT INTO user_credentials VALUES (1, '2026-03-10 12:00:00'), (2, '2026-01-10 12:00:00'), (4, '2026-02-01 08:30:00');
INSERT INTO user_sessions VALUES
  (701, 1, '2026-03-09 08:00:00', '2026-03-20 08:00:00', NULL),
  (702, 1, '2026-03-10 12:05:00', '2026-03-20 12:05:00', NULL),
  (703, 2, '2026-03-05 10:00:00', '2026-03-20 10:00:00', '2026-03-11 09:00:00'),
  (704, 4, '2026-03-12 09:00:00', '2026-03-20 09:00:00', NULL);

-- 漏比對 password_changed_at：被盜舊 Session 701 依然存活
SELECT s.session_id
FROM user_sessions s
JOIN users u ON u.user_id = s.user_id
WHERE u.status = 'active' AND u.deleted_at IS NULL
  AND s.revoked_at IS NULL AND s.expires_at > '2026-03-15 10:00:00'
ORDER BY s.session_id;

-- 補上 s.created_at >= c.password_changed_at：僅放行合法 Session 702
SELECT s.session_id
FROM user_sessions s
JOIN users u ON u.user_id = s.user_id
JOIN user_credentials c ON c.user_id = s.user_id
WHERE u.status = 'active' AND u.deleted_at IS NULL
  AND s.revoked_at IS NULL AND s.expires_at > '2026-03-15 10:00:00'
  AND s.created_at >= c.password_changed_at
ORDER BY s.session_id;
```

```text
漏比對 password_changed_at：[(701,), (702,)]
補齊 password_changed_at：  [(702,)]
```

接著在同一個驗證時間點檢查五把商家 API 金鑰：Key 1 有效、Key 2 **已撤銷但到期日仍在年底**、Key 3 已過期、Key 4 所屬商家 1003 已停權、Key 5 有效且 `expires_at IS NULL`：

```sql
-- SQLite 3.53.0（聚焦布林優先序與 NULL 邊界，省略 key_prefix / key_hash / scopes；'2026-03-15 10:00:00' 為當前驗證時間）
CREATE TABLE merchants (merchant_id INTEGER PRIMARY KEY, status TEXT NOT NULL, deleted_at TEXT);
CREATE TABLE merchant_api_keys (api_key_id INTEGER PRIMARY KEY, merchant_id INTEGER, expires_at TEXT, revoked_at TEXT);

INSERT INTO merchants VALUES (1001, 'active', NULL), (1002, 'active', NULL), (1003, 'suspended', NULL);
INSERT INTO merchant_api_keys VALUES
  (1, 1001, '2026-12-31 23:59:59', NULL),
  (2, 1001, '2026-12-31 23:59:59', '2026-03-01 00:00:00'),
  (3, 1002, '2026-03-01 00:00:00', NULL),
  (4, 1003, NULL,                  NULL),
  (5, 1002, NULL,                  NULL);

-- 錯誤寫法（OR 漏加括號）：AND 綁得比 OR 緊，導致已撤銷的 Key 2 直接繞過認證
SELECT k.api_key_id
FROM merchant_api_keys k
JOIN merchants m ON m.merchant_id = k.merchant_id
WHERE m.status = 'active' AND k.revoked_at IS NULL AND k.expires_at IS NULL
   OR k.expires_at > '2026-03-15 10:00:00'
ORDER BY k.api_key_id;

-- 錯誤寫法（漏寫 IS NULL）：NULL 比較結果為未知而錯誤排除合法的 Key 5
SELECT k.api_key_id
FROM merchant_api_keys k
JOIN merchants m ON m.merchant_id = k.merchant_id
WHERE m.status = 'active' AND m.deleted_at IS NULL
  AND k.revoked_at IS NULL AND k.expires_at > '2026-03-15 10:00:00'
ORDER BY k.api_key_id;

-- 正確寫法：以括號界定 OR 的運算範圍，並同時核對商家狀態與金鑰撤銷
SELECT k.api_key_id
FROM merchant_api_keys k
JOIN merchants m ON m.merchant_id = k.merchant_id
WHERE m.status = 'active' AND m.deleted_at IS NULL
  AND k.revoked_at IS NULL
  AND (k.expires_at IS NULL OR k.expires_at > '2026-03-15 10:00:00')
ORDER BY k.api_key_id;
```

```text
OR 漏加括號：     [(1,), (2,), (5,)] -- 已撤銷的 Key 2 通過認證
漏寫 IS NULL：    [(1,)]             -- 錯誤排除永不過期的合法 Key 5
括號＋完整條件：  [(1,), (5,)]
```

漏加括號的那條查詢沒有任何語法錯誤，開發測試時如果只測了一把正常金鑰與一把過期金鑰（沒有測已撤銷但到期日在未來的金鑰），整套測試就會全數通過（關於引擎只驗合法性而不驗提問正確性的機制見 [SQL.13 查詢的合法性與答案的正確性：引擎檢查的範圍、答案錯掉的成因與查證方法](/backend/01-database/sql/well-formed-is-not-correct/)）。建表階段若改規定所有 API 金鑰都強制設定 `NOT NULL` 到期日，就能把 `IS NULL OR` 這段易錯的布林分支從查詢裡完全移除；如果業務確實需要無期限金鑰，則應將驗權條件封裝在受控檢視表或單一資料存取層函式裡，避免開發者在各個端點重複撰寫。

## 個資分離、受控檢視表與唯附寫稽核的衝突化解

商業系統的設計同時受多項互相牽制的資料保護要求約束：分析團隊需要按地區、方案或商品彙總業務數據，但依最小揭露原則不應接觸顧客姓名、電話、地址與電子郵件；系統對財務與權限變更必須寫入不可竄改的稽核軌跡，防止入侵者事後滅證；個資法規（例如歐盟 GDPR 遺忘權或逾保存期限清理）又要求系統在收到刪除請求後確實抹除個人識別資料。

這些要求若混在同一組資料表裡設計，授權粒度會先出現外洩缺口：當顧客表同時包含分析用欄位（`city`、`created_at`）與明文個資（`name`、`email`、`phone`），又直接把整張表的 `SELECT` 授與商業智慧（Business Intelligence，BI）角色，只在儀表板介面隱藏個資欄位時，任何取得 BI 資料庫存取憑證的人直接執行 `SELECT email FROM customers` 就能全數匯出；把 `email` 做無鹽 MD5 雜湊放給分析師也無效，因為攻擊者對常見信箱名單跑一次同樣雜湊即可反查還原身分（假名化（pseudonymization）與帶金鑰雜湊 HMAC 的邊界見 [7.44 多租戶平台的隔離層級：資料存放、建置管線、營運後台、資料庫管理與備份的權限範圍，跨租戶資料整合，以及事故報告要交代的隔離資訊](/backend/07-security-data-protection/multi-tenant-platform-isolation-tiers/) 的〈跨租戶資料整合與隔離的取捨〉）。

在資料庫層切開暴露面的做法是**結構分離加上受控檢視表**：將電話、住址、統編等高敏感個人資料拆入獨立表（如 `customer_pii` 或 `shipment_recipient_pii`，附帶 `erased_at` 抹除時間戳），主表僅留無業務含意的代理主鍵（surrogate key）與非個資屬性；對分析與 BI 角色撤銷原表與 PII 表的所有權限，僅授與只投影非個資欄位的受控檢視表（view，例如 `v_customer_analytics`）的 `SELECT` 權限。即使分析師對該檢視表執行 `SELECT *`，資料庫也只會回傳代理主鍵與去識別化後的城市分組。這項機制在 PostgreSQL 上成立的前提是檢視表維持預設的 `security_invoker = false` 設定（以檢視表擁有者的權限讀取底表）；若檢視表同時包含 `WHERE` 列過濾條件（例如過濾特定分群或已刪除列），另須加上 `WITH (security_barrier = true)`，防止呼叫端外層非 `LEAKPROOF` 條件被查詢最佳化器下推並藉由錯誤副作用側錄隱藏列。如果底表同時啟用多租戶 RLS 且團隊為套用呼叫端 RLS 而改設 PostgreSQL 15 起的 `security_invoker = true`，呼叫端必須具備底表讀取權限——此時單純靠表級撤權封鎖一張混含個資的底表會發生衝突，可依表結構選用共存路徑：若已將明文 PII 拆入獨立的 `customer_pii` 表，則僅對分析角色撤銷 `customer_pii`、授與無 PII 主表的 `SELECT` 並搭配 `security_invoker = true` 與主表 RLS；若尚未拆表，則改對底表授與欄級權限 `GRANT SELECT (customer_id, city, created_at) ON customers TO bi_role`，搭配 `security_invoker = true` 同時遮蔽 PII 欄位並套用呼叫端 RLS。

除了授權粒度，不可變稽核表與個資抹除要求也會正面衝突。團隊為了快速做出全站變更追蹤，常見做法是建一張通用稽核表，用觸發器（trigger）把變更前後的整列資料轉成 JSON 寫入該表，接著透過權限或觸發器禁止對這張表執行 `UPDATE` 與 `DELETE` 以維持唯附寫（append-only，僅允許新增、禁止修改與刪除）的不可否認性。幾個月後收到收件人或顧客的個資刪除請求時，團隊立刻面臨兩難：刪除或塗改稽核表會破壞法定財務與安全證據鏈，不塗改則讓明文姓名、電話與地址永久留存在唯附寫稽核表與歷史備份裡且無法單獨移除。

在一般不對個資逐筆加密的模型裡，化解這組衝突的做法是在建模當下立下**稽核欄位白名單**：唯附寫稽核表僅設定記錄主鍵參照（`statement_id`、`merchant_id`、`actor_id`）、動作類型與非個資的業務狀態與金額差值的欄位，不收錄個人明文與認證機密；個人明文集中留在可按期限清空欄位的獨立 PII 表裡。以下在 SQLite 3.53.0 示範這組邊界（以 SQLite 觸發器 `RAISE(ABORT, ...)` 中止違規寫入來示範唯附寫保護；在 PostgreSQL 正式環境另須透過角色權限 `REVOKE UPDATE, DELETE, TRUNCATE` 強制執行，因為 PostgreSQL 執行 `TRUNCATE` 時不會觸發列級 `BEFORE DELETE` 觸發器，會直接清空整張表而繞過唯附寫刪除保護，且資料表擁有者可停用觸發器）：

```sql
-- SQLite 3.53.0（RAISE(ABORT, ...) 為 SQLite 觸發器中止單一語句的專用寫法）
-- '2026-03-20 00:00:00' 為示範用抹除時間戳，實務應改用當下時間參數
CREATE TABLE shipment_recipient_pii (
  shipment_id     INTEGER PRIMARY KEY,
  recipient_name  TEXT,
  recipient_phone TEXT,
  erased_at       TEXT
);

CREATE TABLE billing_audit_logs (
  audit_id      INTEGER PRIMARY KEY,
  statement_id  INTEGER NOT NULL,
  before_status TEXT NOT NULL,
  after_status  TEXT NOT NULL,
  created_at    TEXT NOT NULL
);

CREATE TRIGGER trg_audit_no_update BEFORE UPDATE ON billing_audit_logs
BEGIN SELECT RAISE(ABORT, 'billing_audit_logs is append-only'); END;

CREATE TRIGGER trg_audit_no_delete BEFORE DELETE ON billing_audit_logs
BEGIN SELECT RAISE(ABORT, 'billing_audit_logs is append-only'); END;

INSERT INTO shipment_recipient_pii VALUES (7001, '張小華', '+886933000701', NULL);
INSERT INTO billing_audit_logs VALUES (1, 9801, 'draft', 'issued', '2026-03-01 00:05:00');

-- 收到個資刪除請求或逾保存期：清空獨立 PII 表欄位、留下抹除時間戳並查驗結果
UPDATE shipment_recipient_pii
SET recipient_name = NULL, recipient_phone = NULL, erased_at = '2026-03-20 00:00:00'
WHERE shipment_id = 7001;
SELECT * FROM shipment_recipient_pii WHERE shipment_id = 7001;

-- 嘗試修改或刪除唯附寫稽核表：兩者皆遭中止
UPDATE billing_audit_logs SET before_status = 'redacted' WHERE audit_id = 1;
DELETE FROM billing_audit_logs WHERE audit_id = 1;
```

```text
清空獨立 PII 表：[(7001, None, None, '2026-03-20 00:00:00')]
修改稽核表：     billing_audit_logs is append-only
刪除稽核表：     billing_audit_logs is append-only
```

把 PII 拆入獨立表能清空線上資料庫裡的個人明文（線上 `UPDATE` 之後仍須留意 MVCC 舊版本與 WAL／搜尋索引的清理窗口），但已寫入歷史備份（特別是啟用不可變保留鎖的 [WORM Storage（不可變儲存）](/backend/knowledge-cards/worm-storage/) 備份）的獨立 PII 表在保留期屆滿前依然無法單獨修改；若法規要求收到刪除請求後立即讓所有副本失效且須長期留存歷史紀錄，資料建模上可改採每筆或每租戶獨立加密欄位，並在刪除時銷毀對應金鑰（crypto-shredding）。這項機制能成立的必要前提是**對應金鑰必須存放於獨立於該資料庫不可變備份之外的金鑰管理系統或獨立金鑰庫**——若金鑰表與密文同存於該資料庫並一併進入備份，銷毀線上金鑰後舊備份依然能解出明文；其代價是加密欄位無法直接建立範圍或模糊索引（精確比對須另建帶金鑰雜湊索引），且每筆獨立金鑰在大規模消費端受限於金鑰管理配額與費用，實務常改採獨立金鑰庫或每租戶分鑰。備份寫入憑證分離與防覆寫設計見 [7.43 兩個網路之間的連線安全：可達範圍、連線方向與流入的資料、被入侵端改不到的限制、應用層認證、監控主機的位置、金鑰與控制平面、異地備份的寫入憑證與連線紀錄](/backend/07-security-data-protection/cross-network-connection-security/)，加密備份的密碼與主金鑰輪替判斷見 [7.45 加密備份的密碼、key 檔與主金鑰：換密碼與換主金鑰的差別、密碼外洩與遺失的處置，以 restic 為例](/backend/07-security-data-protection/backup-encryption-password-and-master-key/)，刪除閉環與備份保留窗口治理見 [7.11 資料駐留、刪除與證據鏈](/backend/07-security-data-protection/data-residency-deletion-and-evidence-chain/)。

## 角色層的預設權限與資源逾時護欄

即使建表與檢視表切分得再乾淨，上線後的每一次結構遷移（schema migration）都會建立新表，而對外 API 也可能收到合法語法組出的高代價查詢（例如深頁 `OFFSET` 或多重前導萬用字元 `LIKE '%a%b%c%'` 導致主資料庫資源耗盡）。PostgreSQL 18 在角色層提供與資料表治理直接相連的預設權限（`ALTER DEFAULT PRIVILEGES`）與執行逾時（`statement_timeout`、`lock_timeout`、`idle_in_transaction_session_timeout`）設定（以下皆取自 PostgreSQL 18 官方文件〈ALTER DEFAULT PRIVILEGES〉、〈Privileges〉、〈ALTER ROLE〉與〈Client Connection Defaults〉，未於本機實跑）：

- **收緊 `public` 命名空間（[Schema（命名空間義）](/backend/01-database/sql/knowledge-cards/schema-namespace/)）與新建表的預設零權限**：PostgreSQL 15 起對**新建叢集與新建資料庫**預設撤銷 `PUBLIC` 在 `public` schema 上的 `CREATE` 權限，防止一般登入角色在共用 schema 建表或預先建立同名物件攔截查詢（自 PostgreSQL 14 以下透過 `pg_upgrade` 升級或還原 dump 的舊資料庫會保留舊權限，仍須手動 `REVOKE CREATE`）。對於新建資料表，PostgreSQL 預設僅授與建立該表的擁有者全部權限，其餘角色與 `PUBLIC` 預設皆無存取權；這個預設的效果是新建表在顯式 `GRANT` 之前不會被其他角色讀取或寫入，對應含敏感資料或需逐表審核授權的情境（從機制推論；PostgreSQL 18〈Privileges〉未明寫設計意圖；預設對 `PUBLIC` 開放的物件是 `FUNCTIONS`/`PROCEDURES` 的 `EXECUTE` 與 `TYPES`/`DOMAINS` 的 `USAGE`，而不是 `TABLES`）。
- **遷移新增業務表的預設授權與顯式授權路徑**：團隊把遷移角色（`migrator`）與應用角色（`app_role`）、分析角色（`bi_readonly`）切開之後，若只對既有表執行 `GRANT`，下次遷移新增業務表時，應用程式以 `app_role` 查詢新表會立刻收到 `permission denied` 錯誤；若為省略逐表授權而讓應用程式共用 `migrator`，應用程式會取得建表與改表權限而破壞最小權限邊界。後續新表授權有兩條路：一是在業務專用 schema 上對遷移角色設定預設權限——先執行 `GRANT USAGE ON SCHEMA <business_schema> TO <app_role>`（非 `public` 的 schema 預設對其他角色無 `USAGE` 權限，漏設會直接報 `permission denied for schema`），再設定 `ALTER DEFAULT PRIVILEGES FOR ROLE <migrator_role> IN SCHEMA <business_schema> GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO <app_role>`，若新表採用 `SERIAL`/`BIGSERIAL` 主鍵另須設定 `ALTER DEFAULT PRIVILEGES FOR ROLE <migrator_role> IN SCHEMA <business_schema> GRANT USAGE, SELECT ON SEQUENCES TO <app_role>`（或一律改採 `GENERATED ... AS IDENTITY`，否則 `INSERT` 呼叫 `nextval()` 會報 `permission denied for sequence`）。執行 `ALTER DEFAULT PRIVILEGES` 時若省略 `FOR ROLE`，PostgreSQL 預設只將規則套用在當前執行角色未來新建的物件上、不會修改既有表的權限，且預設權限不會從 `NOLOGIN` 群組角色繼承——若改由管理帳號（如 `postgres`）緊急手建表，指定 `FOR ROLE <migrator_role>` 的規則不會觸發；代價則是若團隊在同一個 schema 內建立唯附寫稽核表或 PII 表會被過度授權，須將稽核／PII 移至獨立 schema（採 fail-closed 隔離）或在遷移檔顯式 `REVOKE`。二是維持預設零權限，在每一份版本化遷移檔內顯式宣告新表的最小必要 `GRANT` 並搭配 CI 檢查。
- **查詢逾時（`statement_timeout`）、等鎖逾時（`lock_timeout`）與交易內閒置逾時（`idle_in_transaction_session_timeout`）的預設與風險**：`statement_timeout` 控制單一語句的總執行時間上限，`lock_timeout` 控制單次取得鎖的等待時間上限，`idle_in_transaction_session_timeout` 控制連線開啟顯式交易（例如搭配 `SET LOCAL` 使用的 `BEGIN ... COMMIT`）後閒置未送出語句的上限（PostgreSQL 17 起另提供控制整筆交易總時長的 `transaction_timeout`），這幾項參數在 PostgreSQL 18 的預設值皆為 `0`（不限時）。預設為 `0` 的效果是一般查詢、長批次匯出或備份工具在沒有事先規劃時限的環境下不會被中途取消（從機制推論；PostgreSQL 18〈Client Connection Defaults〉未明寫設計意圖）。在對外公開 API 或報表服務的正式環境裡，不限時會讓單一失控查詢、長等鎖佇列，或交易執行更新後卡在外部 HTTP 呼叫而長期持鎖的連線持續佔用 CPU、鎖與連線池，並阻擋 `VACUUM` 清理，形成 SQL 層的阻斷服務（DoS）攻擊。
- **設定角色逾時的機制邊界**：
  - **啟用 `statement_timeout` 時的等鎖優先序與單次計時**：當 `statement_timeout` 設為非 `0`（已啟用）時，`lock_timeout` 必須小於 `statement_timeout`（依 PostgreSQL 18 文件，若 `lock_timeout >= statement_timeout`，`statement_timeout` 會先觸發而讓等鎖逾時失效；遷移或長批次角色採 `statement_timeout = 0` 配短 `lock_timeout` 時不受此限）。將等鎖上限設得更短可在表鎖或 [Row Lock（列鎖）](/backend/knowledge-cards/row-lock/) 競爭時讓請求快速失敗，避免連線池中的所有連線全數停留在等鎖佇列中；此外 `lock_timeout` 係針對單次取鎖嘗試分別計時，單一語句逐列等待多筆鎖的累計等待仍可能高於單次門檻。
  - **僅於可登入角色新建連線時套用**：PostgreSQL 只會在該**可登入角色（`LOGIN`）建立新連線當下**套用 `ALTER ROLE <login_role> SET ...` 設定的參數，設在 `NOLOGIN` 群組角色上的設定不會被成員繼承，透過 `SET ROLE` 切換角色也不會生效；事故期間調整 `ALTER ROLE ... SET` 亦不會立即更新連線池裡既有長連線的設定，須待連線回收重連才會生效。
  - **`USERSET` 層級的可覆寫與連線池殘留邊界**：這幾項逾時參數皆屬 `USERSET` 層級，互動式 SQL 工作階段的呼叫端可自行執行 `SET statement_timeout = 0` 覆寫設定，因此角色層逾時防護的是經應用層或受控 BI 介面送入的參數失控查詢，而不是可下任意語句的惡意直連工作階段。在 PgBouncer 的交易級連線池（預設不在交易之間執行 `DISCARD ALL`）下，若應用程式的慢報表端點需要單次放寬逾時，必須改用交易內 `SET LOCAL statement_timeout`，不可執行連線層級的 `SET statement_timeout`，否則放寬後的門檻會殘留在共用後端連線上並影響後續 API 請求。
- **依角色分層設定範例**：範例設定如 `ALTER ROLE app_login SET statement_timeout = '3s'`、`ALTER ROLE app_login SET lock_timeout = '1s'`、`ALTER ROLE app_login SET idle_in_transaction_session_timeout = '10s'` 與 `ALTER ROLE bi_login SET statement_timeout = '30s'`（角色名與秒數皆為示範值，實際門檻須依服務請求 P99 延遲、可接受等鎖上限、交易內外部呼叫時間與報表長尾耗時量測決定：門檻過短會提前中止正常的尖峰寫入或報表查詢，門檻過長則無法在連線耗盡前中止失控查詢）。再搭配應用層強制 `LIMIT` 上限、以排序鍵接續的鍵集分頁（Keyset Pagination）與唯讀副本隔離，就能把可用性攻擊面限縮在單一請求範圍內。

## 建表與審查時的資安條件對照

上述各項資料表與查詢邊界設計有一個共同特徵：在開發本機、單租戶假資料與正常流程測試下，省略防線的簡化做法與有防線的做法輸出完全一致；差異只在第一位員工離職、第二個租戶進駐、第一份個資刪除請求送達，或是開發者在某一條查詢裡漏寫條件時才會顯現。下表整理各決定的適用條件、不設防時的後果與事後修改成本，供建表設計與查詢審查時查對：

| 設計決定                                                                                                                       | 觸發採用的條件                                                                                                     | 未設防時的失效形態                                                                                                                                                                                                                                      | 事後改回的遷移成本                                                                                                                                                                                                                                                                              |
| ------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 軟刪除搭配 `WHERE deleted_at IS NULL` 部分唯一索引與 `status = 'active'` 查詢過濾                                              | 帳號或成員表須保留歷史外鍵參照，且允許同信箱重新註冊（同時受個資抹除約束時另須可空 `email`＋`CHECK` 或獨立憑證表） | 整表 `UNIQUE` 擋住復職重註冊；撤除約束引發並行寫入重複信箱；任一查詢漏濾 `deleted_at IS NULL` 或 `status = 'active'` 讓離職帳號仍可通過驗證                                                                                                             | 須清理既有重複列、補建部分唯一索引，並逐條清查全系統所有帳號查詢補上 `deleted_at IS NULL` 與 `status = 'active'` 條件                                                                                                                                                                           |
| 多租戶子表冗餘 `NOT NULL` 租戶鍵＋父表 `UNIQUE` 與複合外鍵＋PostgreSQL `FORCE RLS`                                             | 多客戶共用資料表（pool 模式）且有深層父子表查詢或強制隔離需求                                                      | 把租戶條件寫進 `LEFT JOIN ... ON` 而非 `INNER JOIN`/`WHERE` 導致洩漏全站子表；缺 `FORCE RLS` 或誤用 `SUPERUSER`/`BYPASSRLS` 造成 RLS 靜默繞過；連線池重用連線時漏交易內 `SET LOCAL` 造成跨請求租戶連線變數污染；子表無租戶鍵時 RLS 子查詢退化為全表掃描 | 須替父表補 `UNIQUE (tenant_id, id)`（時間分割表須含分割鍵）、替子表擴充租戶欄、分批回填並設 `NOT NULL`、建複合索引與複合外鍵，並另行規劃 `BYPASSRLS` 備份角色與認證前查表政策（大表分段流程見 [1.6 資料庫轉換實作：雙寫、回填、切流與回滾](/backend/01-database/database-migration-playbook/)） |
| RBAC 改用 `EXISTS` 半連接＋非同步任務表存請求者與範圍並終結未授權任務                                                          | 使用者可同時擁有多個權限重疊的角色，且存在背景高權限任務                                                           | 直接 `JOIN` RBAC 表造成查詢結果列數重複膨脹；背景 worker 未於執行前複查請求者當下狀態與權限時，替已離職或遭撤權人員完成匯出（困惑代理人）；僅略過未終結狀態會堆積殭屍列並在帳號復權後幽靈復活                                                           | 須補齊任務表請求者與範圍欄位，把各 worker 認領邏輯改寫為執行前即時權限複查、併發鎖定與拒絕寫入終態                                                                                                                                                                                              |
| 存取憑證表分離 `key_prefix`/`key_hash`、Session 聯動 `password_changed_at`（或 `sessions_valid_after`）、`AND`/`OR` 條件加括號 | 系統維護可撤銷 Session 或長期 API 金鑰，且允許帳號鎖定、密碼重設或全域登出                                         | 明文金鑰隨資料庫或備份外洩遭直接冒用；密碼重設或撤權後舊 Session 仍可用；`AND`/`OR` 漏加括號讓已撤銷金鑰繞過認證；`expires_at > now` 錯誤排除 `NULL` 永不過期金鑰                                                                                       | 須替 `user_credentials` 帳號存取憑證表或 `users` 補建並回填失效門檻欄位；既有明文金鑰雖可補算雜湊，但因明文已落入歷史備份與快照、無法消除既成暴露風險，仍須全面輪替重發（原存無鹽弱雜湊則技術上無法補算加鹽或換演算法，同樣須全面輪替）；驗權條件須收斂至單一資料存取函式或檢視表               |
| 個資拆入獨立 PII 表＋分析角色僅授受控檢視表（含 `security_barrier`）＋稽核表白名單唯附寫                                       | 系統開放 BI／分析存取，或同時受財務稽核不可變與個資刪除法規管轄                                                    | BI 繞過介面直接匯出明文個資或反查無鹽雜湊；整列 JSON 寫入不可變稽核表導致個資無法抹除、形成合規死鎖                                                                                                                                                     | 事後剝離已混入唯附寫稽核表的明文 PII 必須重建稽核表並破壞既有的不可否認證據鏈，且已寫入歷史備份的明文在保留期屆滿前無法個別移除                                                                                                                                                                 |
| 角色切分搭配 `ALTER DEFAULT PRIVILEGES`（含 `SCHEMA`/`SEQUENCES`）與登入角色分層逾時護欄                                       | 伺服器端關聯式資料庫服務對外公開請求，或多服務／分析人員共用資料庫                                                 | 新建表漏授權導致上線報錯，或共用遷移帳號讓應用程式取得建表與改表權限；單一慢查詢、等鎖佇列或交易內閒置持鎖長期佔用主資料庫連線造成服務中斷                                                                                                              | 須盤點既有物件擁有者與所有服務連線存取憑證，逐一拆分資料庫帳號並輪替存取憑證，並依服務延遲重測 `statement_timeout`、`lock_timeout` 與 `idle_in_transaction_session_timeout` 上限                                                                                                                |

本篇處理的是資料表模型與查詢邊界的設計選擇。當團隊進一步需要評估把租戶切進獨立資料庫（silo）或分群隔離單元（cell）以及共用元件（CI 管線、營運後台、跨租戶彙整庫）的影響範圍時，接續看 [7.44 多租戶平台的隔離層級：資料存放、建置管線、營運後台、資料庫管理與備份的權限範圍，跨租戶資料整合，以及事故報告要交代的隔離資訊](/backend/07-security-data-protection/multi-tenant-platform-isolation-tiers/)；若要把本篇討論的資料表變更安全套用到已經上線的大表上，雙寫、分批回填與切流分段流程見 [1.6 資料庫轉換實作：雙寫、回填、切流與回滾](/backend/01-database/database-migration-playbook/)，選擇由誰產生與何時套用 schema 變更檔以及控制表鎖等待見 [1.20 Schema 變更由誰寫出、何時套用：應用程式啟動時依 model 改 schema、從 model 差異產生 migration 檔、宣告目標 schema 與手寫版本化 migration](/backend/01-database/schema-change-management/)。
