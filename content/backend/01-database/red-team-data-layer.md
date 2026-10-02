---
title: "1.5 攻擊者視角（紅隊）：資料層弱點判讀"
date: 2026-05-13
description: "從資料存取邊界、外洩路徑與修復代價、盤點 database 的主要弱點"
weight: 5
tags: ["backend", "database", "security", "red-team"]
---

資料層紅隊判讀的核心目標是確認「誰能讀到什麼資料、資料會從哪裡流出、錯誤狀態如何回復」。這裡的紅隊指攻擊者視角的風險檢查：從可被濫用的路徑反向檢查資料邊界。database 一旦承擔 [source of truth](/backend/knowledge-cards/source-of-truth/)、弱點就同時影響正確性、隱私與可恢復性。

本章聚焦在 *資料層*（DB 自身）的攻擊面、跟 [7 資安與資料保護模組](/backend/07-security-data-protection/) 的網路 / 身份 / 加密層形成互補。讀完後讀者能盤點：DB 上有哪些 *攻擊路徑*、哪些 *外洩管道*、哪些 *偵測訊號*。

## 資料層弱點的主要軸線

資料層弱點可分成三條軸線：存取邊界、狀態邊界、資料流邊界。

**存取邊界**：看 [authorization](/backend/knowledge-cards/authorization/) 與 [tenant boundary](/backend/knowledge-cards/tenant-boundary/)。哪些 user / role / tenant 可以 read / write 哪些資料。
**狀態邊界**：看 [transaction](/backend/knowledge-cards/transaction/) 與 [isolation level](/backend/knowledge-cards/isolation-level/)。同時讀寫時的 race condition、TOCTOU。
**資料流邊界**：看查詢結果、匯出、備份、觀測與支援工具的資料暴露路徑。

三條軸線各有典型攻擊模式、要分別檢查。

## DB 攻擊面的外圍層次

DB 攻擊面由內到外分成 DB 本身、DB 周邊產品、認證信任根，每一層有典型攻擊向量跟防禦邊界、紅隊盤點要逐層檢查。盤點若只做 DB 本身（SQL injection、帳號權限、加密設定），DB 周邊產品與認證信任根的失守會讓 DB 本身的防禦變成無效投資。

**DB 本身**（最直接、防禦最成熟）— SQL injection、authentication、authorization、RLS 都在這層。

**DB 周邊產品**（最常被忽略）— file transfer service（MFT）、API gateway、search proxy、admin console 都「接 DB」、且通常 perimeter 設定比 DB 鬆。對應 [MOVEit 2023](/backend/07-security-data-protection/red-team/cases/edge-exposure/moveit-2023-mass-exfiltration/) — MOVEit Transfer 是 file transfer 產品、漏洞讓攻擊者直接存取後端資料、屬於 edge-exposure 類別的批量利用事件。判讀重點：任何「接 DB」的產品都屬於 DB 攻擊面、要盤 *所有上游 caller 產品*。類似結構還有 [GoAnywhere MFT 2023](/backend/07-security-data-protection/red-team/cases/data-exfiltration/goanywhere-mft-2023-exfiltration-chain/)、[Progress WS_FTP 2023](/backend/07-security-data-protection/red-team/cases/data-exfiltration/progress-wsftp-2023-file-service-breach/)。

**認證信任根**（最致命、最少人想到）— signing key、token issuer、IAM [federation](/backend/knowledge-cards/federation/) 都決定「誰能宣稱是哪個 user」。對應 [Microsoft Storm-0558](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) — 簽章金鑰外洩後、攻擊者偽造可被驗證的身分權杖、application 層的 BOLA / BOPLA / RLS 都會在底層 trust 失守時被繞過。判讀重點：DB authorization 接受上游認證結果、上游 trust 失守時、DB 層的精緻設計就被旁路掉。

**設計含義**：紅隊盤點順序是由外向內。先盤認證信任根（誰能通過認證）、再盤 DB 周邊產品（通過認證後能打到哪些產品）、最後盤 DB 本身（打到 DB 後能做什麼）。任一層失守、比它更內側的各層的防禦投資都會被旁路。

## 注入類攻擊

**SQL Injection**：

- 經典攻擊、把 user input 拼進 SQL 字串
- 防禦：parameterized query / prepared statement、絕不字串拼接

**NoSQL Injection**：

- MongoDB / DynamoDB 也可能被注入（不同形式）
- MongoDB：`{$where: ...}` operator injection、用 `{$ne: null}` 這類 operator 物件跳過密碼比對
- DynamoDB：FilterExpression 注入（少見、需要特定 application 結構）
- 防禦：白名單 user input、不直接組 query operator

MongoDB 的登入端點把 request body 的欄位原樣放進查詢條件時，`password` 欄位收到的若是 operator 物件而不是字串，查詢比對的就不再是密碼：

```javascript
db.users.insertOne({username: "alice", password: "s3cret"});
// 攻擊者送出的 request body：password 欄位是 operator 物件，不是字串
const body = JSON.parse(`{"username": "alice", "password": {"$ne": null}}`);
// 登入端點把 body 的欄位原樣放進查詢條件
// password 的條件變成「不等於 null」，有設密碼的 alice 就符合，回傳 alice 的文件
db.users.findOne({username: body.username, password: body.password});
// 修法：組查詢前確認 password 是字串；operator 物件在這一步得到 false、被拒絕
typeof body.password === "string";
```

**ORM Injection**：

- 即使用 ORM、`Raw()` / `Exec()` 等 escape hatch 仍能注入
- 用 `where` clause 接 user input 不過濾、ORM 不會自動防
- 防禦：永遠 parameterized、`Raw()` 必須 review

**Second-order Injection**（二階注入）：

- 寫入時用參數化查詢、看起來安全；資料之後被讀出來拼進另一段 query 時才觸發，比寫入當下就觸發的注入更難偵測
- 防禦：*所有* DB output 都當 untrusted、不能依賴「寫入時的 escape」

下面用 Python 的 `sqlite3` 模組示範：註冊端點安全地存下一個帶 SQL 片段的 username，admin 報表把讀出來的 username 拼進查詢字串時，片段才被執行。

```python
import sqlite3

db = sqlite3.connect(":memory:")
db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, email TEXT)")
db.execute("INSERT INTO users (username, email) VALUES ('alice', 'alice@example.com')")
db.execute("INSERT INTO users (username, email) VALUES ('bob', 'bob@example.com')")

# 註冊端點：用參數化查詢寫入，username 原樣存進資料表，這一步沒有注入
signup_name = "x' OR '1'='1"
db.execute("INSERT INTO users (username, email) VALUES (?, ?)",
           (signup_name, "attacker@example.com"))

# admin 報表：從資料表讀出 username，再用字串拼接組下一段查詢
stored_name = db.execute(
    "SELECT username FROM users WHERE email = 'attacker@example.com'").fetchone()[0]
report_sql = "SELECT username, email FROM users WHERE username = '" + stored_name + "'"
print(report_sql)
# SELECT username, email FROM users WHERE username = 'x' OR '1'='1'
print(db.execute(report_sql).fetchall())
# 回傳 alice、bob 與攻擊者自己三列：存進去的片段在這裡變成了條件

# 修法：讀出來的值同樣走參數化查詢
print(db.execute("SELECT username, email FROM users WHERE username = ?",
                 (stored_name,)).fetchall())
# 只回傳攻擊者自己那一列
```

**真實事件對照**：[MOVEit 2023 mass exfiltration](/backend/07-security-data-protection/red-team/cases/edge-exposure/moveit-2023-mass-exfiltration/) 是 SQL injection 升級成 mass data exfil 的代表性事件。Progress Software 的 MOVEit Transfer 是 file transfer 產品、SQL injection 漏洞讓未認證攻擊者直接打到後端 DB、跨上百家客戶持續外洩。這是 DB 周邊產品失守的實例：perimeter 設定比 DB 鬆的 file transfer 產品成為最先被打的點。

對應 [Attack Surface 卡片](/backend/knowledge-cards/attack-surface/) 跟 [7.3 entrypoint security](/backend/07-security-data-protection/entrypoint-and-server-protection/)。

## 授權繞過類攻擊

**BOLA**（Broken Object Level Authorization）：

- 用戶 A 改 user_id 為 B 的請求、後端不檢查就回 B 的資料
- 最常見的 web app 漏洞（OWASP API Top 10 第 1 名）
- 防禦：每個 DB query 都帶 `WHERE owner_id = current_user_id`、不只信 URL parameter
- 對應 [BOLA / IDOR 卡片](/backend/knowledge-cards/bola-idor/)

**BOPLA**（Broken Object Property Level Authorization）：

- 物件級檢查過了、但物件內 *某些屬性* 不該被存取 / 修改
- 例：用戶能更新自己 profile、但不該改 `is_admin` flag
- 防禦：應用層 *allowlist* 屬性、不是 deny-list
- 對應 [BOPLA 卡片](/backend/knowledge-cards/bopla/)

**Mass Assignment**：

- 應用層直接把 request body bind 到 DB row、含未檢查欄位
- 例：`Order.fromJSON(request.body)` 自動 set `is_admin_override` 為 true
- 防禦：明確 allowlist 哪些 field 可從 request 來
- 對應 [Mass Assignment 卡片](/backend/knowledge-cards/mass-assignment/)

**Multi-tenant Boundary Leak**：

- multi-tenant SaaS：tenant A 的 query 不該看到 tenant B 的資料
- 常見錯誤：忘了 `WHERE tenant_id = ?`、用 application 層而非 DB 層強制
- 進階防禦：Row-Level Security（PostgreSQL RLS）、由 DB 強制 tenant boundary

**真實事件對照**：這一節的檢查都接受上游認證結果，身分本身被冒用時一起失效。[Snowflake 2024 credential abuse](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/) 是憑證外洩的例子：攻擊者拿到外洩 credential 後直接 query 多家客戶的 Snowflake account、大量外送資料，防護設計見〈認證 + 網路雙重防護〉。[Microsoft Storm-0558 紅隊版](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) 是認證信任根失守的例子：signing key 洩漏後攻擊者以任意 user 身份查任意 mailbox，application 層的 BOLA / BOPLA 檢查全部照常通過。

## 資料外洩類攻擊

**Excessive Data Exposure**：

- API 回應比需要的多（內部欄位、PII、信用卡末四碼）
- 「前端會 filter」是反模式 — 攻擊者直接看 raw response
- 防禦：DTO / response schema 明確列哪些欄位可回、不要 `SELECT *`
- 對應 [Excessive Data Exposure 卡片](/backend/knowledge-cards/excessive-data-exposure/)

**Log / Trace 洩漏**：

- 把 query 含 PII 直接寫進 log、log 進 SIEM、SIEM 給多人看
- distributed tracing 把 query 跟 user_id 都記下來
- 防禦：log 前 redact、敏感欄位 mask、distributed tracing 的 attribute allowlist

**Backup / Export 洩漏**：

- DB backup 沒加密、放公開 S3 bucket
- 客服 / BI 工具導出 CSV、檔案被搬到不該的地方
- 防禦：backup encryption、export audit、emit-once endpoint
- **真實事件對照**：[LastPass 2022 backup chain](/backend/07-security-data-protection/red-team/cases/data-exfiltration/lastpass-2022-backup-chain/) — 開發環境被入侵後、攻擊者沿著 *備份路徑* 拿到 production vault backup、雖然 vault 內容是加密的、但 master password 弱的客戶可被離線爆破。備份路徑的權限設計見〈備份 vs 正式環境的權限獨立性〉。

**Support Tool Path**：

- 客服 admin 工具可以 query 任何用戶資料
- 內部工具沒有 audit log、不知道誰看了什麼
- 防禦：客服 tool 必須 audit log、敏感欄位 mask、access 按 ticket 限制
- **真實事件對照**：[Okta Support System 事件](/backend/07-security-data-protection/cases/okta-support-system-incident-2023/) — 攻擊者拿到 Okta support 系統存取後、能看到客戶上傳的 HAR 檔（含 session token）、再用 token 進客戶 tenant。Support tool 的 *查詢能力* 跟 *資料分級* 不對等就會放大事故面。

對應 [7.4 data protection and masking](/backend/07-security-data-protection/data-protection-and-masking-governance/) 跟 [7.7 audit trail](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/)。

## 競態 / TOCTOU 類攻擊

**TOCTOU**（Time of Check Time of Use）：

- 檢查時讀到的狀態、到使用時已經被別的 transaction 改掉
- 例：先 SELECT 確認 user 有 100 credit、再 UPDATE 扣 100、中間有別的 transaction 改了 credit
- 防禦：用 `SELECT ... FOR UPDATE` 鎖、或用 atomic operation（把檢查寫進 UPDATE 的條件）

下面的 PostgreSQL 示範讓兩個 session 同時執行同一段交易（實測時在 SELECT 與 UPDATE 之間加一行 `SELECT pg_sleep(2);`，讓兩個 session 交錯）：

```sql
CREATE TABLE accounts (user_id int PRIMARY KEY, credit int NOT NULL);
INSERT INTO accounts VALUES (1, 100);

-- 有競態的寫法：兩個 session 同時跑這一段
BEGIN;
SELECT credit FROM accounts WHERE user_id = 1;   -- 兩個 session 都讀到 100，應用程式都判定夠扣
UPDATE accounts SET credit = credit - 100 WHERE user_id = 1;
COMMIT;
-- 兩段都 commit 之後 credit 是 -100

-- 加鎖的寫法：FOR UPDATE 讓後到的 session 等先到的 commit
BEGIN;
SELECT credit FROM accounts WHERE user_id = 1 FOR UPDATE;
-- 先到的 session 讀到 100；後到的等對方 commit 之後才讀到 0，應用程式據此拒絕扣款
UPDATE accounts SET credit = credit - 100 WHERE user_id = 1;
COMMIT;

-- atomic 寫法：檢查寫進 UPDATE 的條件，不另外讀
UPDATE accounts SET credit = credit - 100 WHERE user_id = 1 AND credit >= 100;
-- 第一次回 UPDATE 1
UPDATE accounts SET credit = credit - 100 WHERE user_id = 1 AND credit >= 100;
-- 第二次回 UPDATE 0：應用程式看影響列數判斷扣款失敗，credit 停在 0
```

**Double-spend 攻擊**：

- 多個 request 同時花同一筆錢
- 防禦：optimistic locking with version、unique constraint、或交易層 serializable
- 詳見 [1.3 Transaction Boundary](/backend/01-database/transaction-boundary/) 的 isolation level 段

**Race condition in business logic**：

- 註冊：兩個 request 同時用同一個 email、可能都成功
- 防禦：unique constraint 在 DB 層、不只 application 層 check

## DoS / 資源耗盡類攻擊

**Unrestricted Resource Consumption**：

- 沒分頁的 `SELECT *`、用戶傳 `?limit=999999`
- 沒 timeout 的長 query
- 防禦：query timeout、pagination 強制上限、rate limit

**Connection 耗盡**：

- 攻擊者開大量 connection、佔光 DB connection pool
- 防禦：connection pool 限制、application 層 connection limit、PgBouncer 共享

**Storage 灌爆**：

- API 允許大量 insert、storage 被填滿
- 防禦：rate limit、quota per tenant、auto-archive

對應 [Unrestricted Resource Consumption 卡片](/backend/knowledge-cards/unrestricted-resource-consumption/)。

## 何時要提高紅隊檢查優先級

下列訊號出現時、資料層弱點通常會放大成系統風險：

- 角色與租戶模型快速增加、且查詢條件跨多個權限層
- migration 頻率提高、且 schema 與讀寫流程同時變更
- 匯出、對帳、客服查詢與搜尋索引共用同一批敏感欄位
- 事故修復高度依賴人工 SQL 與臨時腳本
- 新引入的 ORM / query builder / cache layer 改變了 query 路徑

## 失敗代價

資料層弱點會把單點錯誤轉成長尾影響。

- **越權查詢**：直接資料洩漏 → 通知監管 + 客戶 + 媒體
- **交易邊界混亂**：部分寫入與狀態偏移 → 對帳成本 + 退款處理
- **資料外洩進 log / backup**：拉長處理週期 → 跨 team 清理
- **support tool 濫用**：無 audit log → 無法追究、信任成本上升
- **業務全面中斷**：資料事件升級成 availability 事件、整條業務鏈停擺

這些問題的共同代價是：修復路徑長、稽核負擔高、信任成本上升。

**真實事件對照**：[Change Healthcare 2024 ops impact](/backend/07-security-data-protection/red-team/cases/data-exfiltration/change-healthcare-2024-ops-impact/) 是「資料事件變成業務連續性事件」的代表。攻擊者進入 DB 後、不只外洩資料、還破壞處理能力、讓整個美國醫療支付網路停擺數週。判讀重點：DB 失守不只代表 *資料外洩* 一種損失、還可能直接停掉 *上游業務流程*、評估代價時要把這層算進去。[MGM 2023 identity lateral impact](/backend/07-security-data-protection/red-team/cases/identity-access/mgm-2023-identity-lateral-impact/) 是另一個對照：vishing 拿到 identity 後橫向到核心系統、酒店訂房 / 自助 check-in / 老虎機全停。資料層的攻擊代價要跨業務流量去評估、不只看 DB 本身。

## Incident 三角：DB 事故的同步處置

DB 事故的處置三角是 *同步* 執行三件事、共同消除攻擊者在處置間隙繼續入侵的時間窗：

1. **漏洞修補**：補上被利用的具體漏洞或 misconfiguration
2. **Session / 憑證失效**：撤銷所有可能被攻擊者拿到的 session、token、credential
3. **異常痕跡清查**：盤點攻擊者已經做了什麼、哪些資料動過、哪些 backdoor 留下

同步執行的理由是 *攻擊者擁有平行能力*：用已拿到的 credential 在 patch 完成前重新進入、或用清查前還沒被發現的 backdoor 繞過修補。線性執行「先修漏洞、再失效憑證、再清查」時，憑證失效之前攻擊者仍能用已拿到的 credential 重新進入、清查完成之前仍能走還沒被發現的 backdoor，這兩段時間窗都會放大攻擊代價。

**對應 [MOVEit 2023](/backend/07-security-data-protection/red-team/cases/edge-exposure/moveit-2023-mass-exfiltration/)** — CL0P 從 2023 年 5 月 27 日起利用這個當時還未公開的 SQL injection 漏洞（CVE-2023-34362），攻擊早於 vendor 公告與修補，等 vendor patch 來不及。實務做法是：

- **發布前**：對外服務建立 *即時隔離開關*、不等 vendor patch
- **事故中**：先把入口下線（DNS 切走 / WAF rule 全擋）、同步進行 patch + token revoke + audit log review
- **前提**：事先有 inventory（知道哪些產品接 DB）+ 自動化失效能力（不是手動逐個 revoke）

這個三角是 *能力前提*、不是 *當下決策*。事故當下發現缺哪一角、就只能線性執行、攻擊代價會被放大。

## 偵測與審計

紅隊檢查不只「找漏洞」、也要設計 *持續偵測*：

### Query audit

- DB query 寫進 audit log（誰、什麼時候、查了什麼）
- 不只 admin tool、application 也要 audit
- 對應 [Audit Log 卡片](/backend/knowledge-cards/audit-log/)

### Anomaly detection

- 異常 query pattern（突然 SELECT 全表、跨 tenant 範圍）
- 異常 export volume
- Cross-tenant token 異常（同一 issuer 出現本不應跨域的軌跡）
- 對應 [7.13 detection coverage](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)

Cross-tenant token 偵測是觀測單一 issuer 發出的 token 在不應跨域的 tenant 出現的能力。對應 [Microsoft Storm-0558](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) — 偽造 token *形式上完全合法*、單看 token validation 找不到異常、要看 *軌跡*（哪個 issuer 的 token 跨了哪些 tenant、跟歷史 baseline 比對）。這層偵測需要 application 跟 DB layer 都記下「token 來源 → tenant 目的」的對應、才能事後比對。

對應 [Snowflake 2024](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/) 揭露的異常查詢偵測維度：

- query 體積異常（單一 user 短時間內查詢量遠超日常）
- 來源 IP 異常（從合法網段突然變成未知 endpoint）
- 跨 schema scan 模式（單一 user 突然查多個 tenant 的表）
- 匯出頻率異常（單位時間匯出次數遠超基線）

這些維度都需要足夠歷史 telemetry 建立基線、新部署的 DB 在累積基線前處於偵測盲區、要靠 *絕對閾值* 補（例如「任何 user 單次查詢 > 1GB 都告警」、不等基線）。

### DB-level monitoring

- slow query log（可能是 attacker 在 enumerate）
- failed login（DB 層 connection attempt）
- privilege escalation event

### Periodic review

- 每季 review role / permission
- 每年 audit support tool access pattern
- migration 後重新檢查 access boundary

## 認證 + 網路雙重防護

DB 認證 = 資料邊界、但雲端資料平台（Snowflake、BigQuery、Cosmos DB）預設未必開 MFA、且 *網路層通常 open*（任何 IP 都能嘗試連線）。認證層與網路層都沒有設防時，一組外洩的 credential 就足以從任意 IP 登入。

對應 [Snowflake 2024](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/) — 外洩 credential + 未強制 MFA + 沒設 network policy → 攻擊者直接從任意 IP 用 leaked credential 登入、查多家 tenant 的資料。

**雙重防護設計**：

- **網路層**：network rule allowlist（只允許公司 IP / VPN / 雲端 NAT 連線）— leaked credential 即使有效、也碰不到 DB
- **認證層**：強制 MFA + 條件式存取（context-aware：時間 / 地點 / 裝置）— 即使網路層失守、credential 還要過 MFA
- **應用層**：API key / service account 跟 user credential 分開、各有 lifecycle

網路層與認證層各自獨立設防，其中一層失守時另一層仍能阻擋資料外送。資料平台預設應強制 MFA + network policy、把「credential 外洩 = 資料外送」這條捷徑切斷。

## 批量憑證撤銷的工程能力

批量憑證撤銷能力是事故當下「攔停攻擊者」的核心動作、要 *快速、大量、選擇性* 執行可疑憑證撤銷。這個能力屬於 *事先準備*、事故當下臨時建來不及。

**最小能力清單**：

- **Credential inventory**：列出所有 active credential（user password、API key、service account token、session）。事故當下若靠工程師記憶查、會漏掉長期沒人動的 service account 或 OAuth integration、變成攻擊者 persist 的後門。Inventory 要 *自動產生*、不是人工維護的 spreadsheet。
- **分批撤銷 API**：能按 user group / service / scope 批次撤銷、不是逐個 revoke。批次需要 idempotency key、避免重複撤銷產生競爭。受影響範圍大時、逐個撤銷可能需要數小時、攻擊者持續外送資料。
- **撤銷後 audit**：撤銷紀錄要存（誰被撤、什麼時間、什麼原因、誰執行）、避免事後爭議。
- **重新發放流程**：撤銷後使用者要重新登入、SSO + MFA 流程在事故當下要能撐住瞬間湧入的重新驗證請求。若流程卡住、會在「沒攻擊但用戶進不來」狀態下被迫降回安全等級較低的應急 fallback、形成新攻擊面。

對應 [Snowflake 2024](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/) 的事故處置 — 平台級事故影響數百家客戶、撤銷必須跨 tenant 同步進行、單一客戶手動撤銷來不及。

## 長期可重複匯出工件

Long-lived repeatable export artifact 是事故後仍能持續產出資料的工件、屬於跨事故時間軸的 attack surface。攻擊者拿到一次、就能長期外送、不需要每次重新進入系統。常見類型：

- **預先生成的報表 URL**（內部 BI tool 給 download link、URL 通常長期有效）
- **API key 綁定的 export endpoint**（key 沒過期、endpoint 一直能匯出最新資料）
- **資料平台的 scheduled / saved query**（以合法 user 身份定期執行匯出）
- **Database backup 的 share link**（雲端儲存的 signed URL、有效期可達數年）

**防禦設計**：

- **預設短 TTL**：所有匯出 URL / signed link 預設 1-24 小時失效
- **單次性匯出**：sensitive export 限定 emit-once、用過就失效
- **匯出記錄審計**：每次匯出寫進 audit log、定期審查哪些 endpoint 異常高頻使用

對應 [Snowflake 2024](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/) 連結的紅隊 problem-card「Long-lived repeatable export artifact」— 這類工件的核心風險是 *憑證撤銷後仍可運作*、修復不只要撤 credential、還要盤所有由該 credential 建立的長效工件。

## 備份 vs 正式環境的權限獨立性

備份系統是 *獨立* 的攻擊面、跟正式環境要 *不同權限域*。常見錯誤是「備份用同一組 IAM principal 跟同一把 KMS key」、結果正式環境被打、攻擊者沿著 *備份路徑* 拿到所有歷史資料。

對應 [LastPass 2022 backup chain](/backend/07-security-data-protection/red-team/cases/data-exfiltration/lastpass-2022-backup-chain/) — 開發環境被入侵後、攻擊者沿著備份路徑拿到雲端備份的加密保管庫資料、形成長尾資料保護壓力。判讀重點：備份的 *存放位置*、*金鑰管理*、*存取權限* 都是攻擊面、不只 production DB；備份檔加密本身不足以擋下取走後的離線分析。

**權限獨立性設計**：

- **不同 IAM principal**：production 跟 backup 用不同 service account、production 帳號沒有 backup 讀權限
- **不同 KMS key audience**：production 用 production key、backup 用 backup key、兩者 lifecycle 分離
- **不同 audit log**：production read / write 跟 backup read 在 *不同* audit stream、後續調查能區分「正常運作」vs「備份被讀」
- **不同 access pattern review**：定期審查哪些 principal 在哪些時段讀 backup（正常情況很少有人讀 backup、頻繁讀取是異常訊號）

「正式環境的接管不直接通到備份」是設計準則、不是 best practice 加分項。對應 [1.9 reconciliation](/backend/01-database/reconciliation-data-repair/) 的備份 / PITR 段討論。

## 最低控制面

資料層在討論具體服務前、先定義四個控制面最穩定：

1. **權限模型**：資料存取與角色、租戶、操作情境的對應關係
2. **交易與一致性模型**：哪些操作必須同成敗、哪些可以延遲一致
3. **資料分級與遮罩模型**：哪些欄位可回傳、可觀測、可匯出
4. **恢復模型**：錯誤資料如何比對、回復、追蹤與稽核

## 案例對照

### 資安與資料保護模組的主案例（產品 / 平台事故）

| 案例                                                                                                      | 跟資料層的關係                                           |
| --------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| [Cloudflare Route Leak](/backend/07-security-data-protection/cases/cloudflare-route-leak-2026/)           | 控制面變更可能影響資料層存取                             |
| [Cloudflare Token 事件](/backend/07-security-data-protection/cases/cloudflare-control-plane-token-2023/)  | Token 洩漏 → DB 存取被濫用                               |
| [Azure AD 2021](/backend/07-security-data-protection/cases/azure-ad-identity-control-plane-2021/)         | identity failure → 應用 fallback、可能讓 DB 存取錯誤路徑 |
| [Microsoft Storm-0558](/backend/07-security-data-protection/cases/microsoft-storm-0558-signing-key-2023/) | signing key 洩漏 → 任意 user 身份、可 query 任何資料     |
| [Okta Support System](/backend/07-security-data-protection/cases/okta-support-system-incident-2023/)      | support tool 洩漏 → 客戶資料被存取                       |
| [Okta Cross-Tenant](/backend/07-security-data-protection/cases/okta-cross-tenant-impersonation-2023/)     | tenant boundary 失守 → DB-level RLS 也擋不住             |

### 資安與資料保護模組的紅隊案例（攻擊鏈 / 入侵路徑）

| 紅隊案例                                                                                                                                                   | 攻擊鏈到資料層的路徑                                                        |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| [Snowflake 2024 憑證濫用](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/)                          | 外洩 credential + 未強制 MFA → 直接 query 多家 tenant 資料                  |
| [LastPass 2022 備份鏈](/backend/07-security-data-protection/red-team/cases/data-exfiltration/lastpass-2022-backup-chain/)                                  | 開發環境 → production backup 路徑 → 客戶加密 vault 外送                     |
| [MOVEit 2023 mass exfiltration](/backend/07-security-data-protection/red-team/cases/edge-exposure/moveit-2023-mass-exfiltration/)                          | file transfer 產品零時差 → 後端資料批量外送                                 |
| [Change Healthcare 2024 ops impact](/backend/07-security-data-protection/red-team/cases/data-exfiltration/change-healthcare-2024-ops-impact/)              | DB 入侵 → 醫療支付網路全面停擺、資料事件升級成業務中斷                      |
| [Microsoft Storm-0558 signing key chain](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) | signing key 洩漏 → 任意身份 token forge → application BOLA / BOPLA 全部失效 |
| [MGM 2023 identity lateral impact](/backend/07-security-data-protection/red-team/cases/identity-access/mgm-2023-identity-lateral-impact/)                  | 社交工程 → identity lateral → 業務系統全停、資料層攻擊代價跨業務流量        |

紅隊案例庫的完整入口看 [紅隊案例參考地圖](/backend/07-security-data-protection/red-team/cases/case-reference-map/) — 那邊有按攻擊階段（exposure / exfiltration / identity / supply-chain）的完整索引。

## 跨模組路由

- race condition / TOCTOU 的 isolation level 處理：[Transaction Boundary](/backend/01-database/transaction-boundary/)
- repository adapter 套用 allowlist / parameterized query：[Repository Adapter](/backend/01-database/repository-adapter/)
- state ownership 決定哪些資料需要嚴格存取控制：[State Ownership](/backend/01-database/state-ownership-query-boundary/)
- identity / authorization 邊界：[Identity & Access Boundary](/backend/07-security-data-protection/identity-access-boundary/)
- 資料保護與遮罩：[Data Protection and Masking](/backend/07-security-data-protection/data-protection-and-masking-governance/)
- audit trail：[Audit Trail and Accountability Boundary](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/)
- detection coverage：[Detection Coverage and Signal Governance](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- 事故時的資料層判讀：[Incident Decision Log](/backend/08-incident-response/incident-decision-log/)
- 合規驅動的多 region 部署選型：[Aurora global database 多 region](/backend/01-database/vendors/aurora/global-database-multi-region/)、[Aurora 跨 AZ failover RTO](/backend/01-database/vendors/aurora/cross-az-failover-rto/)、[Data Residency 知識卡](/backend/knowledge-cards/data-residency/)

## 關聯卡片

- [Attack Surface](/backend/knowledge-cards/attack-surface/)
- [Trust Boundary](/backend/knowledge-cards/trust-boundary/)
- [Excessive Data Exposure](/backend/knowledge-cards/excessive-data-exposure/)
- [BOLA / IDOR](/backend/knowledge-cards/bola-idor/)
- [BOPLA](/backend/knowledge-cards/bopla/)
- [Mass Assignment](/backend/knowledge-cards/mass-assignment/)
- [Audit Log](/backend/knowledge-cards/audit-log/)
- [Data Reconciliation](/backend/knowledge-cards/data-reconciliation/)
- [Tenant Boundary](/backend/knowledge-cards/tenant-boundary/)
- [Unrestricted Resource Consumption](/backend/knowledge-cards/unrestricted-resource-consumption/)
