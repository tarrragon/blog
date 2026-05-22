---
title: "MySQL Audit Log + SIEM"
date: 2026-05-22
description: "MySQL audit log、general log、slow log、privilege event、SIEM pipeline、retention 與 alert route"
tags: ["backend", "database", "mysql", "audit", "siem", "security"]
---

MySQL audit log + SIEM 的核心責任是把資料庫操作事件轉成可查詢、可保留、可告警的安全證據。Audit log 是可調查的行為紀錄；它要回答誰在何時、從哪裡、對哪個資料物件做了什麼，以及是否符合授權流程。

本文的判讀錨點是：audit logging 要服務於 investigation 與 compliance。Slow query log、general log、binary log、error log、managed service audit log、plugin audit log 各自承擔不同證據，不應混成同一種 log。

## Event Taxonomy

Event taxonomy 的核心責任是定義要蒐集哪些資料庫事件。

| Event 類型           | 目的                               |
| -------------------- | ---------------------------------- |
| Login / logout       | 身份與來源追蹤                     |
| Failed access        | brute force、credential misuse     |
| DDL                  | schema 變更與 migration evidence   |
| DCL                  | grant / revoke / role 變更         |
| Sensitive read       | PII / payment / high-risk table    |
| Data modification    | bulk update / delete、admin action |
| Replication / backup | binlog、backup、restore access     |

事件分類要對應 alert。DDL 可以進 release audit；failed login 可以進 security alert；sensitive read 要連到 support ticket 或 break-glass 流程。

## Log Sources

Log sources 的核心責任是選出合適來源。

| Source                       | 適合用途                          | 風險                               |
| ---------------------------- | --------------------------------- | ---------------------------------- |
| Error log                    | startup、crash、replication error | 缺少完整 query context             |
| Slow log                     | performance investigation         | 安全事件覆蓋不足                   |
| General log                  | debug / short-term tracing        | volume 大、PII 風險高              |
| Binary log                   | data change recovery / CDC        | 需要解析、並非 user audit 完整替代 |
| Audit plugin / managed audit | security evidence                 | provider / edition / config 限制   |

General log 在 production 要謹慎使用。它能提供完整 SQL，但 volume、PII 與成本都高；通常只用短時間 incident window 或測試環境。

## SIEM Pipeline

SIEM pipeline 的核心責任是把 database event 轉成集中查詢與告警。

| Pipeline step | 內容                                       |
| ------------- | ------------------------------------------ |
| Collect       | log file、managed log export、agent        |
| Normalize     | actor、source IP、database、object、action |
| Mask          | 移除 SQL literal / PII                     |
| Retain        | retention、legal hold、storage class       |
| Alert         | rule、severity、owner、runbook             |
| Review        | periodic access review                     |

Normalization 要避免把完整 SQL 直接送進 SIEM。對敏感系統，可保留 query fingerprint、table、operation、row count、actor 與 ticket id，而非 literal value。

## Alert Rules

Alert rules 的核心責任是把高風險事件變成可行動訊號。

| Rule                       | 代表風險                             | 第一反應                         |
| -------------------------- | ------------------------------------ | -------------------------------- |
| Admin login outside window | credential misuse / emergency access | 確認 ticket、限制 session        |
| Grant / revoke event       | 權限邊界變更                         | access review                    |
| Drop / truncate table      | destructive DDL                      | freeze release、restore decision |
| Bulk update / delete       | application bug / misuse             | 查 transaction、binlog、backup   |
| Sensitive table read       | PII exposure                         | ticket match、scope review       |

Alert 要有 owner 與 runbook。只把 log 送進 SIEM，缺少 triage rule，incident 時仍然難以快速定位。

## Retention and Privacy

Retention and privacy 的核心責任是讓 audit log 同時可用與合規。Audit log 可能包含帳號、IP、SQL、table name、literal value 與 PII；保存時間越長，保護責任越重。

Retention policy 要定義：

1. 保存天數與 storage class。
2. 哪些欄位可被 masked。
3. 誰能查 audit log。
4. Legal hold 如何覆蓋一般 retention。
5. Export 到外部 SIEM 的資料邊界。

Audit log 本身也要納入 access control。能查敏感 audit 的人，通常也能推斷敏感資料活動。

## 下一步路由

Audit log + SIEM 完成後，加密與憑證讀 [Encryption / TLS / Key Management](../encryption-tls-key-management/)；備份事故讀 [PITR / Backup](../pitr-backup/)；安全治理讀 [Data Protection](/backend/07-security-data-protection/data-protection-and-masking-governance/)。
