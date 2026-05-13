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

## 攻擊模式 1：注入類

**SQL Injection**：

- 經典攻擊、把 user input 拼進 SQL 字串
- 防禦：parameterized query / prepared statement、絕不字串拼接
- 二階注入：input 已存進 DB、後續 query 時才觸發 — 比一階更難偵測

**NoSQL Injection**：

- MongoDB / DynamoDB 也可能被注入（不同形式）
- MongoDB：`{$where: ...}` operator injection、`{$ne: null}` 跳過 auth
- DynamoDB：FilterExpression 注入（少見、需要特定 application 結構）
- 防禦：白名單 user input、不直接組 query operator

**ORM Injection**：

- 即使用 ORM、`Raw()` / `Exec()` 等 escape hatch 仍能注入
- 用 `where` clause 接 user input 不過濾、ORM 不會自動防
- 防禦：永遠 parameterized、`Raw()` 必須 review

**Second-order Injection**：

- 第一次寫入時看起來安全、第二次讀出來時觸發
- 例：username 帶 SQL fragment、寫入時 escape、後續 admin 查詢時不 escape
- 防禦：*所有* DB output 都當 untrusted、不能依賴「寫入時的 escape」

**真實事件對照**：[MOVEit 2023 mass exfiltration](/backend/07-security-data-protection/red-team/cases/edge-exposure/moveit-2023-mass-exfiltration/) 是 SQL injection 升級成 mass data exfil 的代表性事件。Progress Software 的 MOVEit Transfer 是 file transfer 產品、漏洞讓未認證攻擊者直接打到後端 DB、跨上百家客戶持續外洩。判讀重點：file transfer 這類「次要產品」也接 DB、且因為通常 perimeter 設定鬆、變成最先被打的點。

對應 [Attack Surface 卡片](/backend/knowledge-cards/attack-surface/) 跟 [7.3 entrypoint security](/backend/07-security-data-protection/entrypoint-and-server-protection/)。

## 攻擊模式 2：授權繞過類

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

**真實事件對照**：[Snowflake 2024 credential abuse](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/) 揭露 *資料平台帳號沒強制 MFA* 的代價、攻擊者拿到外洩 credential 後直接 query 多家客戶的 Snowflake account、大量外送資料。判讀重點：DB 認證 = 資料邊界、但雲端資料平台預設未必開 MFA、要主動 enforce。對應 [Microsoft Storm-0558 紅隊版](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) — signing key 洩漏後攻擊者直接以任意 user 身份查任意 mailbox、application 層 BOLA / BOPLA 全部失效、因為攻擊者通過了底層 trust boundary。

## 攻擊模式 3：資料外洩類

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
- **真實事件對照**：[LastPass 2022 backup chain](/backend/07-security-data-protection/red-team/cases/data-exfiltration/lastpass-2022-backup-chain/) — 開發環境被入侵後、攻擊者沿著 *備份路徑* 拿到 production vault backup、雖然 vault 內容是加密的、但 master password 弱的客戶可被離線爆破。判讀重點：備份檔案的 *存放位置* 跟 *加密狀態* 是攻擊面、不只 production DB。

**Support Tool Path**：

- 客服 admin 工具可以 query 任何用戶資料
- 內部工具沒有 audit log、不知道誰看了什麼
- 防禦：客服 tool 必須 audit log、敏感欄位 mask、access 按 ticket 限制
- **真實事件對照**：[Okta Support System 事件](/backend/07-security-data-protection/cases/okta-support-system-incident-2023/) — 攻擊者拿到 Okta support 系統存取後、能看到客戶上傳的 HAR 檔（含 session token）、再用 token 進客戶 tenant。Support tool 的 *查詢能力* 跟 *資料分級* 不對等就會放大事故面。

對應 [7.4 data protection and masking](/backend/07-security-data-protection/data-protection-and-masking-governance/) 跟 [7.7 audit trail](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/)。

## 攻擊模式 4：競態 / TOCTOU 類

**TOCTOU**（Time of Check Time of Use）：

- 檢查時是 A 狀態、用的時候是 B 狀態
- 例：先 SELECT 確認 user 有 100 credit、再 UPDATE 扣 100、中間有別的 transaction 改了 credit
- 防禦：用 `SELECT ... FOR UPDATE` 鎖、或用 atomic operation（`UPDATE ... WHERE credit >= 100`）

**Double-spend 攻擊**：

- 多個 request 同時花同一筆錢
- 防禦：optimistic locking with version、unique constraint、或交易層 serializable
- 詳見 [1.3 Transaction Boundary](/backend/01-database/transaction-boundary/) 的 isolation level 段

**Race condition in business logic**：

- 註冊：兩個 request 同時用同一個 email、可能都成功
- 防禦：unique constraint 在 DB 層、不只 application 層 check

## 攻擊模式 5：DoS / 資源耗盡類

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

## 偵測與審計

紅隊檢查不只「找漏洞」、也要設計 *持續偵測*：

### 1. Query audit

- DB query 寫進 audit log（誰、什麼時候、查了什麼）
- 不只 admin tool、application 也要 audit
- 對應 [Audit Log 卡片](/backend/knowledge-cards/audit-log/)

### 2. Anomaly detection

- 異常 query pattern（突然 SELECT 全表、跨 tenant 範圍）
- 異常 export volume
- 對應 [7.13 detection coverage](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)

### 3. DB-level monitoring

- slow query log（可能是 attacker 在 enumerate）
- failed login（DB 層 connection attempt）
- privilege escalation event

### 4. Periodic review

- 每季 review role / permission
- 每年 audit support tool access pattern
- migration 後重新檢查 access boundary

## 最低控制面

資料層在討論具體服務前、先定義四個控制面最穩定：

1. **權限模型**：資料存取與角色、租戶、操作情境的對應關係
2. **交易與一致性模型**：哪些操作必須同成敗、哪些可以延遲一致
3. **資料分級與遮罩模型**：哪些欄位可回傳、可觀測、可匯出
4. **恢復模型**：錯誤資料如何比對、回復、追蹤與稽核

## 案例對照

### 07 主案例（產品 / 平台事故）

| 07 案例                                                                                                        | 跟資料層的關係                                           |
| -------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| [7.C1 Cloudflare Route Leak](/backend/07-security-data-protection/cases/cloudflare-route-leak-2026/)           | 控制面變更可能影響資料層存取                             |
| [7.C2 Cloudflare Token 事件](/backend/07-security-data-protection/cases/cloudflare-control-plane-token-2023/)  | Token 洩漏 → DB 存取被濫用                               |
| [7.C3 Azure AD 2021](/backend/07-security-data-protection/cases/azure-ad-identity-control-plane-2021/)         | identity failure → 應用 fallback、可能讓 DB 存取錯誤路徑 |
| [7.C4 Microsoft Storm-0558](/backend/07-security-data-protection/cases/microsoft-storm-0558-signing-key-2023/) | signing key 洩漏 → 任意 user 身份、可 query 任何資料     |
| [7.C5 Okta Support System](/backend/07-security-data-protection/cases/okta-support-system-incident-2023/)      | support tool 洩漏 → 客戶資料被存取                       |
| [7.C6 Okta Cross-Tenant](/backend/07-security-data-protection/cases/okta-cross-tenant-impersonation-2023/)     | tenant boundary 失守 → DB-level RLS 也擋不住             |

### 07 紅隊案例（攻擊鏈 / 入侵路徑）

| 紅隊案例                                                                                                                                                   | 攻擊鏈到資料層的路徑                                                        |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| [Snowflake 2024 憑證濫用](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/)                          | 外洩 credential + 未強制 MFA → 直接 query 多家 tenant 資料                  |
| [LastPass 2022 備份鏈](/backend/07-security-data-protection/red-team/cases/data-exfiltration/lastpass-2022-backup-chain/)                                  | 開發環境 → production backup 路徑 → 客戶加密 vault 外送                     |
| [MOVEit 2023 mass exfiltration](/backend/07-security-data-protection/red-team/cases/edge-exposure/moveit-2023-mass-exfiltration/)                          | file transfer 產品 SQL injection → 跨上百家客戶 DB 外送                     |
| [Change Healthcare 2024 ops impact](/backend/07-security-data-protection/red-team/cases/data-exfiltration/change-healthcare-2024-ops-impact/)              | DB 入侵 → 醫療支付網路全面停擺、資料事件升級成業務中斷                      |
| [Microsoft Storm-0558 signing key chain](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) | signing key 洩漏 → 任意身份 token forge → application BOLA / BOPLA 全部失效 |
| [MGM 2023 identity lateral impact](/backend/07-security-data-protection/red-team/cases/identity-access/mgm-2023-identity-lateral-impact/)                  | 社交工程 → identity lateral → 業務系統全停、資料層攻擊代價跨業務流量        |

紅隊案例庫的完整入口看 [紅隊案例參考地圖](/backend/07-security-data-protection/red-team/cases/case-reference-map/) — 那邊有按攻擊階段（exposure / exfiltration / identity / supply-chain）的完整索引。

## 跨模組路由

1. 與 1.3 的交接：race condition / TOCTOU 用 [transaction boundary](/backend/01-database/transaction-boundary/) 的 isolation level 處理
2. 與 1.4 的交接：repository adapter 應用 allowlist / parameterized query — [repository adapter](/backend/01-database/repository-adapter/)
3. 與 1.8 的交接：state ownership 決定哪些資料需要嚴格存取控制 — [State Ownership](/backend/01-database/state-ownership-query-boundary/)
4. 與 7.2 的交接：identity / authorization 邊界 — [Identity & Access Boundary](/backend/07-security-data-protection/identity-access-boundary/)
5. 與 7.4 的交接：資料保護與遮罩 — [Data Protection and Masking](/backend/07-security-data-protection/data-protection-and-masking-governance/)
6. 與 7.7 的交接：audit trail — [Audit Trail and Accountability Boundary](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/)
7. 與 7.13 的交接：detection coverage — [Detection Coverage and Signal Governance](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
8. 與 8.19 的交接：事故時的資料層判讀 — [Incident Decision Log](/backend/08-incident-response/incident-decision-log/)

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
