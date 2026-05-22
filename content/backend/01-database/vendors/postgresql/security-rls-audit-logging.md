---
title: "PostgreSQL Security / RLS / Audit Logging"
date: 2026-05-22
description: "PostgreSQL role、grant、Row Level Security、pgAudit、log policy、PII access evidence 與合規路由"
tags: ["backend", "database", "postgresql", "security", "rls", "audit"]
---

PostgreSQL security / RLS / audit logging 的核心責任是把資料庫安全拆成存取邊界、資料列可見性與操作證據。PostgreSQL role / grant 決定誰能連線與操作 schema；[Row Level Security](/backend/knowledge-cards/row-level-security/) 決定同一張表中哪些 row 對某個 role 可見；audit logging 則把敏感操作轉成可查詢、可保留、可告警的證據。

本文的判讀錨點是：資料庫安全是 application auth 的下游防線。Application 仍要負責身份、session、租戶與 workflow；PostgreSQL security layer 負責在資料邊界補上 least privilege、tenant isolation 與 forensic evidence。

## Role and Grant Baseline

Role and grant baseline 的核心責任是把人、服務、migration 與分析查詢分開。Production database 至少要區分 application role、migration role、read-only role、admin role 與 replication / CDC role。

| Role 類型         | 權限責任                         | 常見風險                          |
| ----------------- | -------------------------------- | --------------------------------- |
| Application       | 執行產品讀寫                     | 權限過大、可 DDL、可讀所有 schema |
| Migration         | 變更 schema                      | 和 app 共用 role，事故難以追蹤    |
| Read-only         | 分析、debug、support             | 讀到 PII 或跨 tenant 資料         |
| Replication / CDC | logical replication、slot access | 權限與 WAL retention 風險         |
| Admin             | emergency operation              | 日常使用 admin role               |

Grant review 要以 schema ownership 開始。Tables、sequences、functions、views、extensions 都有權限面；只管 table grant 會漏掉 sequence update、function execution 與 extension 使用。

## Row Level Security

Row Level Security 的核心責任是在資料庫層 enforce row visibility。PostgreSQL 官方 RLS 文件描述 policy 可限制 normal query 返回、insert、update、delete 的 row；這讓 tenant boundary 可以在 database 層多一道 guard。

| RLS 使用情境      | 適合條件                            | 審查問題                                 |
| ----------------- | ----------------------------------- | ---------------------------------------- |
| Multi-tenant SaaS | tenant_id 明確且每個 query 都可帶入 | policy 是否覆蓋 SELECT / INSERT / UPDATE |
| Support access    | support role 需受限查詢             | break-glass 是否有 audit                 |
| Regional data     | row 上有 region / residency         | policy 是否和 GDPR / residency 對齊      |
| Sensitive subset  | PII row 需特別隔離                  | masking / tokenization 是否仍需存在      |

RLS policy 要有 positive allow rule。每張啟用 RLS 的 table 都要有測試：同 tenant 可讀、跨 tenant 隔離、insert tenant mismatch 被擋、admin / support 例外被記錄。

```sql
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON invoices
USING (tenant_id = current_setting('app.tenant_id')::uuid)
WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);
```

這段 policy 依賴 application 在 transaction 內設定 `app.tenant_id`。使用 connection pooler 時，設定必須跟 transaction boundary 對齊，避免 session state 漂移。

## Audit Logging

Audit logging 的核心責任是把敏感資料操作轉成可查詢證據。PostgreSQL 原生日誌可以記錄連線、DDL、錯誤與慢查詢；pgAudit 這類 extension 則補強 session / object audit。

| Audit 類型       | 目的                             | Evidence                                 |
| ---------------- | -------------------------------- | ---------------------------------------- |
| DDL audit        | schema 變更追蹤                  | migration id、role、statement、timestamp |
| Sensitive read   | PII / payment / health data 查詢 | role、tenant、operation、reason          |
| Privilege change | grant / revoke / role 變更       | actor、target role、approval             |
| Failed access    | 權限錯誤與 RLS block             | error code、role、relation               |
| Break-glass      | emergency admin access           | ticket id、duration、review result       |

Audit log 要能進入 SIEM 或集中 log。只留在 database host 上，事故後查詢成本高；正式 runbook 要定義 retention、masking、access control 與 alert。

## PII and Data Protection Boundary

PII and data protection boundary 的核心責任是把 database 權限和資料保護策略接起來。RLS 可以限制 row visibility，但 PII 的保護還需要 masking、tokenization、encryption、retention 與 deletion evidence。

| 資料類型         | Database control               | 跨模組路由                                                                                      |
| ---------------- | ------------------------------ | ----------------------------------------------------------------------------------------------- |
| Tenant data      | RLS、tenant-scoped role        | data access review                                                                              |
| PII              | column grant、masking view     | [Data Protection](/backend/07-security-data-protection/data-protection-and-masking-governance/) |
| Audit log        | append-only storage、retention | SIEM / incident evidence                                                                        |
| Deletion request | tombstone、cascade review      | retention policy、legal hold                                                                    |

Column-level grant 和 masking view 適合 read-only analyst。Application role 通常需要明文處理 workflow；analyst / support role 則應走 restricted view。

## Operational Evidence

Operational evidence 的核心責任是讓安全設定可驗證。每次 release 或權限變更後，要跑固定檢查。

1. Role matrix：每個 role 的 schema / table / sequence / function grant。
2. RLS test：tenant A / tenant B / support / admin 的可見性測試。
3. Audit sample：DDL、sensitive read、failed access 是否進 log。
4. Pooler compatibility：`SET LOCAL app.tenant_id` 是否跟 transaction 對齊。
5. Break-glass drill：emergency access 是否可申請、可回收、可審查。

Evidence 要保存在 release artifact。Security 設定只有文件描述時，incident 後難以證明它真的生效。

## Failure Modes

Failure modes 的核心責任是把 database security 常見事故提前列出。

| Failure mode       | 判讀訊號                        | 修正方向                                 |
| ------------------ | ------------------------------- | ---------------------------------------- |
| App role 權限過大  | app 可 DDL / drop / grant       | role split + least privilege             |
| RLS bypass         | owner / superuser / policy 漏洞 | dedicated app role + RLS test            |
| Pooler state drift | tenant setting 漂到下個 request | `SET LOCAL` + transaction pooling review |
| Audit gap          | 敏感操作查不到 actor            | pgAudit / log schema / SIEM route        |
| Support overread   | support role 可讀全 tenant      | masking view + ticket-scoped access      |

RLS bypass 要特別審查 table owner 與 superuser path。正式 application 連線應使用 dedicated role，並避免使用 table owner role 執行一般 request。

## 下一步路由

Security / RLS / audit logging 完成後，權限與 PII 治理讀 [Data Protection](/backend/07-security-data-protection/data-protection-and-masking-governance/)；connection state 風險讀 [Connection Pooler Comparison](../connection-pooler-comparison/)；實作演練可放進 [Schema Migration Evidence Lab](../hands-on/schema-migration-evidence-lab/) 的 release gate。
