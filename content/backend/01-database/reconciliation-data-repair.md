---
title: "1.9 Reconciliation 與 Data Repair"
date: 2026-05-11
description: "說明資料錯誤發生後如何驗證、修復、稽核與回寫事故證據。"
weight: 9
tags: ["backend", "database", "reconciliation", "data-repair"]
---

Reconciliation 與 data repair 的核心責任是把資料錯誤從模糊異常轉成可驗證、可修復、可稽核的流程。進入特定資料庫或 ORM 前，讀者需要先理解資料修復屬於正式狀態責任的一部分。

## Reconciliation

Reconciliation 的責任是比較兩個或多個資料來源，確認正式狀態是否與外部事實一致。付款狀態要和金流 provider 對齊，發票狀態要和開票系統對齊，庫存狀態要和出貨或倉儲系統對齊。

對帳需要明確定義資料來源、時間窗、比對鍵、差異分類與 owner。這些欄位能把「資料看起來不一致」轉成可分派、可修復、可驗證的決策材料。

## Data Repair

Data repair 的責任是把已確認的資料差異修回正式狀態，並保留修復原因、範圍、證據與回退條件。修復可以是 SQL update、補事件、補發 webhook、重建 projection 或人工客服流程，但每種修復都要有範圍控制。

資料修復要先分成三種：

| 類型         | 說明                          | 常見風險                       |
| ------------ | ----------------------------- | ------------------------------ |
| 欄位修復     | 修正單筆或小批正式欄位        | mapping 規則錯誤會造成二次污染 |
| 派生狀態重建 | 重建 index、cache、read model | 可能掩蓋正式狀態尚未修復       |
| 補償動作     | 補退款、補發票、補通知        | 可能產生重複副作用             |

修復前要先確認問題落在哪一層。正式欄位錯誤要修 source of truth；派生狀態錯誤要重建副本；外部副作用漏做要走補償流程。

欄位修復的判讀重點是 mapping 規則是否正確，因為錯誤規則會把單點差異擴成批次污染。派生狀態重建的判讀重點是 source of truth 是否已經正確，否則重建會複製錯誤。補償動作的判讀重點是副作用是否可逆，因為退款、通知或外部 webhook 可能已經被使用者或第三方看見。

## Repair Runbook

Repair runbook 的責任是讓資料修復可重複執行，並降低對當下工程師記憶的依賴。最小 runbook 需要包含：

1. 差異查詢與 query link。
2. 影響範圍與 tenant / region / time range。
3. 修復方式與 dry-run 結果。
4. 審核 owner 與執行 owner。
5. rollback condition 與後續 validation query。

runbook 要和 [validation query](/backend/knowledge-cards/validation-query/) 共用語意。若查詢與修復程式用不同 mapping 規則，修復結果就難以被同一份 evidence 驗證。

## Audit 與權限邊界

Data repair 常常需要高權限，因此必須接到 audit 與資料保護邊界。修復個資、付款、權限或方案資料時，要保留操作者、審核者、查詢範圍、寫入範圍與修復前後樣本。

這裡要接到 [7.7 Audit Trail 與 Accountability Boundary](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/)。資料修復同時是可靠性、資安與合規問題。

## Evidence Handoff

資料修復的 evidence handoff 要能支援 release gate 與 incident review。

| 欄位         | 內容                                             |
| ------------ | ------------------------------------------------ |
| Source       | reconciliation query、provider report、audit log |
| Time range   | 差異發生窗口與修復窗口                           |
| Query link   | mismatch sample、修復前後驗證                    |
| Owner        | data owner、service owner、reviewer              |
| Data quality | 抽樣覆蓋率、延遲、未覆蓋資料                     |
| Known gap    | 尚未確認的 provider callback、低流量 tenant      |

這份 handoff 要進入 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 與 [8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)。

## 實體服務討論承接點

實體資料庫文章要承接本篇的 reconciliation 與 data repair 責任。PostgreSQL、MySQL、MSSQL 或其他資料庫的差異，應放在它們如何產生 validation query、保留 audit trail、支援 point-in-time recovery、處理 replica lag 與控制修復權限。

若服務需要高頻對帳，後續文章要比較查詢成本、索引策略與 replica 讀取延遲。若服務需要高風險資料修復，後續文章要比較 transaction log、backup/restore、row-level audit 與權限分離。若服務需要跨系統補償，後續文章要把資料庫能力接到 queue replay 與 incident decision log。

## 下一步路由

要處理 migration 造成的資料差異，接著讀 [1.7 Schema Migration Rollout 證據](/backend/01-database/schema-migration-rollout-evidence/)。要處理事件漏發造成的副作用修復，接著讀 [3.8 Queue Consumer Retry 與 Replay Handoff](/backend/03-message-queue/queue-consumer-retry-replay-handoff/)。
