---
title: "Cloud-native Data Policy (BigQuery + S3)"
date: 2026-05-18
description: "BigQuery column / row-level security + S3 bucket policy + Access Points + Macie、雲端原生資料層 access control、跟 DLP / Purview 互補"
weight: 7
tags: ["backend", "security", "vendor", "cloud-data-policy", "bigquery", "s3", "data-control"]
---

Cloud-native data policy 的核心責任是把資料層的 access 控制綁在 *storage resource 本身*、用該雲既有的 IAM 體系做 enforcement、不依賴額外的 data security platform。本頁同時涵蓋 *BigQuery policy tooling*（Authorized View / Column-level security / Row-level security / Dynamic Data Masking）跟 *AWS S3 policy tooling*（Bucket policy / Access Points / Object Lambda / Macie / Block Public Access）— 兩條 sister stack 是各自雲端代表性的 data access control 設計、合一頁是為了讓讀者看清楚 *GCP 走 SQL-native 細粒度* 跟 *AWS 走 storage-resource-bound* 的取捨差異、不是把它們當同類混寫。

## 服務定位

Cloud-native data policy 是 *resource-bound* access control — 控制邏輯掛在 BigQuery dataset / column / row 或 S3 bucket / object 上、用 [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/) / [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) 的 principal 體系做 evaluation。跟 [Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) 比、DLP 是 *content-based discovery + transformation*（掃 PII、做 de-id）、本頁工具是 *access boundary*；典型組合是 *DLP 發現 sensitive column → BigQuery policy tag 控制誰能讀 → S3 Object Lambda redact at read time*。跟 [Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/) 比、Purview 走 *label-driven + 跨 platform*（同一個 sensitivity label 跨 SharePoint / Fabric / Azure SQL）、雲端原生 policy 走 *resource-bound + 限該雲*；雲端原生更貼近 storage、跨雲統一靠商業 platform。跟通用 [Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/) 比、IAM 是 *resource-level read/write 二分*、本頁是 *column / row / object-level 細粒度*、補 IAM 解不掉的「同一張表只能看自家行」場景。

關鍵張力：*資料細粒度* ↔ *跨雲 portability*。BigQuery RLS 跟 S3 Access Points 的 policy 語法都是該雲專屬、換雲要重寫；換來的是 free（無額外授權）+ 平台原生效能（不過代理）。多雲 enterprise 若要統一 policy DSL、走 Immuta / Privacera / Snowflake Horizon。

## 本章目標

讀完本頁、讀者能判斷：

1. BigQuery 跟 S3 policy 各自能做到什麼層級的細粒度（column / row / object / cross-region）、不能做到什麼
2. Cloud-native policy 跟 [Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) / [Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/) 的責任分界、何時要組合使用
3. Multi-tenant SaaS 在共用 dataset / bucket 場景的 access boundary 設計（BigQuery RLS / S3 Access Points）
4. 何時用雲端原生 policy、何時改走 Immuta / Privacera / Snowflake 跨雲 data security platform

## 最短判讀路徑

判斷 cloud-native data policy 是否健康、最少看四件事：

- **BigQuery 側 — RLS / column policy coverage**：multi-tenant dataset 是否有 `CREATE ROW ACCESS POLICY`、sensitive column 是否綁 policy tag、policy tag 上的 IAM 是否走 group 而非 individual user、view-only access 是否走 [Authorized View](https://cloud.google.com/bigquery/docs/authorized-views) 而非 dataset grant
- **S3 側 — bucket policy 結構**：Block Public Access 是否 account-level 開啟、ACL 是否 disabled（Object Ownership = BucketOwnerEnforced）、共用 bucket 是否走 Access Points 分租戶、跨帳號是否經 AP policy + bucket policy 雙重驗證
- **Sensitive data discovery 接口**：BigQuery 是否接 [Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) inspection job、Dataplex 是否跑 data classification、S3 是否開 Macie scan、findings 是否進 EventBridge / Security Hub 而非僅 console 看
- **Audit trail completeness**：BigQuery audit log（dataAccess）是否進 [Cloud Logging](/backend/04-observability/) + 進 SIEM、S3 是否開 server access logging + CloudTrail data event（GetObject / PutObject）、跟 [Detection Coverage](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) 對齊

四件事任一缺失、就是 [Data Residency, Deletion and Evidence Chain](/backend/07-security-data-protection/data-residency-deletion-and-evidence-chain/) 邊界的待補項目。

## 日常操作與決策形狀

### BigQuery 側

**Authorized View / Authorized Routine**：view 的 SQL definition 可以讀 source dataset、grantee 只要被 grant view 自身就能查、*不需要 grant source dataset access*。經典「給 analyst 看 aggregate 數據但不給原始 PII row」模式 — analyst 看 `SELECT region, count(*) FROM customer` 沒問題、但 underlying `customer` table 從不出現在 analyst IAM。Authorized Routine 是同邏輯延伸到 stored procedure / UDF、適合 logic 比 SELECT 複雜的轉換場景。

**Column-level security（policy tag）**：在 [Data Catalog](https://cloud.google.com/data-catalog) 建 taxonomy + policy tag、把 BigQuery column schema 綁 tag、policy tag 上設 *fine-grained reader* role。沒這個 role 的 user 即使有 dataset access、`SELECT *` 時該 column 會 *raise error* 或 *被 omit*。HIPAA / PCI-DSS 對「即使 DBA 也不能 default 看到 PHI / cardholder data」的硬要求、走 policy tag 是技術性 enforcement、不是 procedural control。

**Row-level security (RLS)**：`CREATE ROW ACCESS POLICY tenant_filter ON dataset.table GRANT TO ('group:analysts@org.com') FILTER USING (tenant_id = SESSION_USER())`。每個 query 自動 append filter、user 看到的 row 由 policy expression 決定。Multi-tenant SaaS（共用 dataset、每行帶 `tenant_id`）必用 — 否則 query 必須在 application layer 帶 WHERE、漏一處就是跨 tenant data leak。對應 [Snowflake 2024 Credential Abuse](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/) 的對照啟示。

**Dynamic Data Masking**：column 上設 masking rule（hash / nullify / partial mask / regex replace）、不同 IAM 角色看不同 mask 程度 — `email_address` 在 admin 看到原值、在 analyst 看到 `***@example.com`、在 external partner 看到 NULL。補 RLS 不足之處：RLS 過濾 *哪些 row 看得到*、Masking 過濾 *看到的 row 內容怎麼呈現*；兩者組合解大多數 multi-tenant + multi-role 場景。

**Dataplex Data Classification + DLP 整合**：Dataplex 走 lake-wide 治理（dataset metadata + lineage + quality）、自動觸發 [Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) inspection、發現 sensitive column 自動建議 / 套用 policy tag。是 GCP 內部把 *discovery → access control* 自動化的標準路徑。

### S3 側

**Block Public Access account-level**：2018 推出、2023 起新建 bucket 預設開啟。account-level setting 強制 override 所有 bucket policy / ACL — 即使有 bucket policy 寫 `"Principal": "*"`、Block Public Access 開啟時也禁止對外暴露。Production AWS 帳號必須 account-level 開、bucket-level 額外加固。是 [LastPass 2022 Backup Chain](/backend/07-security-data-protection/red-team/cases/data-exfiltration/lastpass-2022-backup-chain/) 類事故的 last-line defense。

**Bucket policy / IAM policy / ACL（legacy）**：三層 evaluation — bucket policy（resource-based、寫在 bucket 上）、IAM policy（identity-based、寫在 principal 上）、ACL（legacy object-level、新建 bucket 應禁用）。AWS 2023 起推 *Object Ownership = BucketOwnerEnforced*、強制 ACL disabled、所有 access 經 bucket policy + IAM 決定。舊 bucket 應走 ACL → bucket policy migration。

**S3 Access Points**：每個 bucket 可開多個 Access Point、各有獨立 name + policy + VPC restriction。Multi-tenant 場景（一個 bucket 服務多個 tenant）走「每個 tenant 一個 AP + AP policy 限定 prefix + 限定 VPC」、取代過去「shared bucket + prefix-based IAM」的脆弱模式。對應 [Mailchimp 2023 Support Tool Abuse](/backend/07-security-data-protection/red-team/cases/data-exfiltration/mailchimp-2023-support-tool-abuse/) 的對照啟示 — 共用入口需 *per-tenant policy boundary*、不是 application-layer filtering。

**Multi-Region Access Points (MRAP)**：跨 region replicated bucket 的單一 global endpoint、自動 route 到最近 region。資料駐留要求高的場景（GDPR / 中國資料法）反而要慎用、因為 read 來源不可預測；對 latency-sensitive 全球分發是 first-class 解法。

**Object Lambda Access Points**：在 GetObject response path 插 Lambda、做 *read-time transformation*（redact PII / format conversion / image resize / decrypt + re-encrypt）。同一份 raw object、不同 caller 透過不同 Object Lambda AP 看到不同版本 — 等同 BigQuery Dynamic Data Masking 在 S3 的對應物。但 Lambda 有 cold start + 6MB response limit、不是所有場景都合適。

**Macie sensitive data discovery**：S3 專屬、scan bucket 找 PII / credential / payment data、findings 進 EventBridge + AWS Security Hub。跟 [Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) 同層但限 S3、不能掃 RDS / DynamoDB。findings 應自動 route 到 SIEM、不是只在 Macie console 等人看。對應 [Progress WS_FTP 2023 File Service Breach](/backend/07-security-data-protection/red-team/cases/data-exfiltration/progress-wsftp-2023-file-service-breach/) 的對照 — 對外檔案服務必有 audit + 異常量 baseline + Macie sensitive content scan。

**S3 Object Ownership / ACL disabled**：2023+ 預設 ACL disabled、所有新 bucket 應 keep this default、舊 bucket 走 audit + migration（先掃 ACL grant、確認沒人靠 ACL 拿 access、再切換）。混用 ACL + bucket policy 的 bucket 是 access control 漂移最常見的源頭。

## 核心取捨表

| 取捨維度            | BigQuery policy tooling                             | S3 policy tooling                                     | Immuta / Privacera                        | Snowflake Horizon                   |
| ------------------- | --------------------------------------------------- | ----------------------------------------------------- | ----------------------------------------- | ----------------------------------- |
| 細粒度層級          | Column / Row / cell-level（policy tag + RLS + DDM） | Object-level（prefix-based）+ Object Lambda 內容轉換  | Column / Row / cell + 跨平台統一 DSL      | Column / Row + Snowflake 平台限定   |
| 計費                | Free（included in BigQuery）                        | Free（bucket policy）+ Macie / Object Lambda 用量計費 | 商業授權、per-user 或 per-data-source     | Snowflake 平台費內含                |
| 跨雲 portable       | GCP only                                            | AWS only                                              | 跨 BigQuery / Snowflake / Databricks / S3 | Snowflake only                      |
| Policy DSL          | SQL-native（CREATE ROW ACCESS POLICY、masking SQL） | JSON policy + Lambda 程式碼                           | 統一 attribute-based DSL                  | SQL-native                          |
| Sensitive discovery | DLP / Dataplex 自動整合                             | Macie（限 S3）                                        | 內建 + 跨平台 scan                        | 跨 schema metadata + classification |
| Audit               | Cloud Audit Log dataAccess 細到 column              | CloudTrail data event + server access log             | 跨平台統一 audit trail                    | Snowflake QUERY_HISTORY             |
| 適合場景            | GCP-first、BigQuery 為主 data warehouse             | AWS-first、S3 為 data lake / 檔案分發                 | 多雲 enterprise、跨平台統一 policy        | Snowflake-centric data platform     |
| 退場成本            | 中 — RLS / policy tag 重寫到目標平台                | 中 — bucket policy / AP 重寫                          | 低 — DSL 抽象可遷移                       | 中 — 限 Snowflake                   |

選雲端原生 policy 的核心訴求：*單一雲 + 預算敏感 + 不想引入新 vendor*。多雲 enterprise + 統一治理需求高、走 Immuta / Privacera 才能避免兩套 policy 漂移。

## 進階主題

**BigQuery Authorized View vs RLS 取捨**：Authorized View 適合 *shape-based filtering*（grantee 只能看 aggregate / 特定 column subset）、RLS 適合 *value-based filtering*（grantee 只能看 tenant_id = self 的行）。實務常常組合 — view 限 column、view 上再加 RLS 限 row。view 的問題是維護成本（schema 改要同步改 view）、RLS 的問題是 policy expression 寫錯整批 user 看不到資料、staging tenant 跑過再 promote。

**S3 Access Points + VPC-only restriction**：AP policy 可加 `"Condition": {"StringEquals": {"aws:SourceVpc": "vpc-xxx"}}`、強制只能從特定 VPC access — 跨帳號場景（partner 帳號 access 自家 bucket）必加、避免 partner credential 外洩後可從任意網路位置存取。對應 [LastPass 2022 Backup Chain](/backend/07-security-data-protection/red-team/cases/data-exfiltration/lastpass-2022-backup-chain/) 對照、backup bucket 不該跟 prod bucket 共用 IAM role + 不該允許 internet-wide access。

**Object Lambda redact PII at read time**：適合 *raw data 已寫入、但不同 consumer 需要不同 view* 的場景 — 例如客服查 user record 看到 mask 過的 SSN、合規 audit 帳號看到完整 SSN。Lambda 內部呼叫 [Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) deid template / Comprehend PII detection / 自家 regex；要注意 cold start 對 latency 的影響、不適合 high-throughput 場景。

**Macie automated discovery → SIEM**：Macie findings 走 EventBridge rule → Security Hub → 推 [Splunk / Elastic Security / Datadog Security](/backend/07-security-data-protection/vendors/) — 不該只在 Macie console 看 findings。發現 unencrypted S3 bucket 有 cardholder data 必須觸發 incident response runbook、進 [8 事故處理](/backend/08-incident-response/)。

**跨 region 跟 data residency**：BigQuery dataset region + S3 bucket region 是 *資料駐留 enforcement* 的硬邊界、policy tooling 不能 override。GDPR / 中國資料法場景必須 *region pinning* + 禁止 Multi-Region replication、policy tag / RLS 無法解決資料離境問題。對應 [Data Residency Deletion and Evidence Chain](/backend/07-security-data-protection/data-residency-deletion-and-evidence-chain/) 章節原則。

## 排錯與失敗快速判讀

- **BigQuery RLS 設了但 user 還是看到全部 row**：policy `GRANT TO` 沒包該 user 的 group、或 user 有 `bigquery.dataOwner` role（owner override RLS）— check group membership + 降權到 dataViewer
- **Column policy tag 沒生效**：column 沒 attach tag、或 tag taxonomy 沒在該 project / region — check Data Catalog taxonomy location 跟 dataset region 對齊
- **S3 bucket 意外 public**：Block Public Access account-level 沒開 + bucket policy 寫 `"Principal": "*"`、或 ACL 殘留 AllUsers grant — 立即開 BPA + audit ACL（aws s3api get-bucket-acl）
- **Access Point policy 跟 bucket policy 衝突**：AP 允許 但 bucket policy 拒絕、最後是拒絕（explicit deny 永遠勝）— 兩層都要明確 allow、bucket policy 加 `"Principal": {"AWS": "*"}` + condition 限定 AP ARN
- **Macie scan 跑很久 / cost 暴衝**：scan 整個 bucket、含 archive prefix、沒設 sampling — 用 *sensitive data discovery job* with prefix filter + sampling rate、不要 default 全 bucket scan
- **Authorized View grantee 看不到資料**：view definition 走的 source dataset 沒 authorize 該 view、或 view 自身改了但沒重新 authorize — `bq update --view_authorization` 重設
- **Object Lambda 慢 / timeout**：Lambda cold start + 6MB response limit、大檔案不該走 Object Lambda — 改在寫入時 transform、或用 pre-signed URL 繞過 Object Lambda

## 何時改走其他服務

| 需求形狀                                 | 改走                                                                                                                                                          |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 跨雲統一 data policy DSL                 | Immuta / Privacera                                                                                                                                            |
| Content-based discovery + de-id          | [Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) / [Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/) |
| Label-driven + Microsoft 365 跨 platform | [Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/)                                                                          |
| Application-layer access control         | 應用層 RBAC / ABAC（Casbin / OPA / Cerbos）                                                                                                                   |
| Snowflake-centric data platform          | Snowflake Horizon（row access policy / masking policy 平台內建）                                                                                              |
| 通用 cloud resource permission           | [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) / [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/)         |
| SIEM / detection                         | [Splunk / Elastic Security / Datadog Security](/backend/07-security-data-protection/vendors/)                                                                 |

## 不在本頁內的主題

- BigQuery / S3 自身的完整 admin guide（pricing / region / quota）
- Encryption-at-rest 細節（KMS 整合走 [AWS KMS](/backend/07-security-data-protection/vendors/aws-kms/) / [Google Cloud KMS](/backend/07-security-data-protection/vendors/google-cloud-kms/) 頁）
- Azure Data Lake / Azure SQL policy（屬 Azure stack、本頁不涵蓋）
- 應用層 RBAC framework（Casbin / Cerbos / OPA Rego）
- 資料庫層 RLS（PostgreSQL RLS / SQL Server Row-Level Security）— 跟雲端原生 storage policy 是不同層

## 案例回寫

Cloud-native data policy 在 07 案例庫沒有直接 vendor-level 事件、所有 data exfiltration case 都是 access boundary 的對照：

| 案例                                                                                                                                                       | 跟 cloud-native data policy 的關係（對照啟示）                                                                                                                                     |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Snowflake 2024 Credential Abuse](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/)                  | Multi-tenant SaaS 共用 dataset / schema 必須有 BigQuery RLS / Snowflake row access policy 等技術邊界、即使 credential 外洩攻擊者也只能看授權 row、不能只靠 application-layer WHERE |
| [LastPass 2022 Backup Chain](/backend/07-security-data-protection/red-team/cases/data-exfiltration/lastpass-2022-backup-chain/)                            | S3 backup bucket 跟 prod bucket 必須獨立 Access Point + 獨立 IAM role + VPC restriction、同帳號 prefix-based 區隔不夠、Block Public Access 是 last-line                            |
| [Progress WS_FTP 2023 File Service Breach](/backend/07-security-data-protection/red-team/cases/data-exfiltration/progress-wsftp-2023-file-service-breach/) | 對外檔案服務必須有 S3 server access log + CloudTrail data event + Macie sensitive content scan、批量下載靠 GetObject 速率 baseline alert、不是事後檢視                             |
| [Mailchimp 2023 Support Tool Abuse](/backend/07-security-data-protection/red-team/cases/data-exfiltration/mailchimp-2023-support-tool-abuse/)              | 共用 bucket 服務多 tenant 必走 S3 Access Points 拆 per-tenant policy、取代 prefix-based ACL 跟 application-layer filtering 的脆弱模式                                              |
| [Data Residency Deletion and Evidence Chain (section)](/backend/07-security-data-protection/data-residency-deletion-and-evidence-chain/)                   | Cloud-native policy 是 deletion + residency 治理的技術 enforcement 層、region pinning + 禁止 Multi-Region replication + audit log retention 對應章節原則                           |

## 下一步路由

- 上游：[7.7 資料駐留刪除與證據鏈](/backend/07-security-data-protection/data-residency-deletion-and-evidence-chain/)、[Detection Coverage and Signal Governance](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- 平行：[Google DLP](/backend/07-security-data-protection/vendors/google-dlp/)（discovery + de-id 互補）、[Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/)（label-driven 對照）
- 下游：[Splunk / Elastic Security / Datadog Security](/backend/07-security-data-protection/vendors/)（audit log + Macie findings → SIEM）
- 跨類：[AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) / [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/)（principal 體系基底）、[AWS KMS](/backend/07-security-data-protection/vendors/aws-kms/) / [Google Cloud KMS](/backend/07-security-data-protection/vendors/google-cloud-kms/)（encryption-at-rest）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（data exfiltration incident routing）、[1 資料庫模組](/backend/01-database/)（database-layer RLS / column policy 對照）
- 官方：[BigQuery column-level security](https://cloud.google.com/bigquery/docs/column-level-security)、[BigQuery row-level security](https://cloud.google.com/bigquery/docs/row-level-security-intro)、[Amazon S3 Access Points](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-points.html)、[Amazon Macie](https://docs.aws.amazon.com/macie/)
