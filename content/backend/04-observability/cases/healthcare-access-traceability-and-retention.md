---
title: "Healthcare：存取可追溯性與保留邊界"
date: 2026-05-07
description: "在資料主權限制下，建立可追溯存取證據與分層保留策略。"
weight: 3
tags: ["backend", "observability", "case-study"]
---

本案例的核心責任是讓資料主權場景下的觀測仍可追溯。Healthcare 系統常同時面臨最小存取原則、資料留存規範與跨團隊協作需求。

## 業務背景

一個遠距醫療平台，服務多家醫療機構（multi-tenant），處理病歷查閱、處方開立、檢驗報告與預約排程。平台受 HIPAA 跟當地個資法規範，稽核單位要求能回答「哪個使用者在什麼時間查看了哪個病患的哪份紀錄」。

初期系統的存取紀錄散落在各服務的 application log 中 — 病歷服務記了一筆 `GET /patient/123/records`，處方服務記了一筆 `POST /prescription`，但兩者沒有共同的 correlation key。稽核問「護理師 A 在 3 月 15 日存取了哪些病歷」時，工程師需要在四個服務各自 grep，再用 timestamp 近似對齊，整個流程耗時半天且結果不可靠。

## 技術挑戰

### 存取 log 與 application log 混合

存取紀錄（誰看了什麼）跟 operational log（request timing、error、retry）寫在同一個 pipeline。Application log 的 retention 設定 30 天（除錯夠用），但法規要求存取紀錄保留 6 年。等到稽核來查詢時，超過 30 天的存取紀錄已經被刪。

### 跨服務存取鏈斷裂

一次病歷查閱可能經過 API gateway → auth service → patient service → record service → audit service 五個服務。每個服務各自記 log，但沒有統一的 access event correlation。Auth service 知道「誰」，patient service 知道「看了哪個病患」，record service 知道「看了哪份紀錄」— 三段資訊散落在三個服務的 log 中，無法自動關聯。

### Multi-tenant retention 差異

不同醫療機構受不同法規管轄 — 機構 A 在美國需要 HIPAA 6 年 retention，機構 B 在歐盟需要 GDPR 的「目的限縮」原則（保留期限隨用途而定），機構 C 在台灣需要醫療法規定的 7 年。統一 retention policy 要嘛過度保留（增加成本與 PII 暴露面），要嘛保留不足（法規風險）。

## 解法

### Data access audit log 獨立 pipeline

把存取事件從 application log 分離出來。每當使用者查閱、修改或匯出 PHI（Protected Health Information）時，產生結構化 access event：

```json
{
  "event_type": "phi_access",
  "actor": "nurse-a@hospital-x.com",
  "patient_id": "P-2048",
  "resource": "medical_record/lab_result/2026-03-15",
  "action": "view",
  "trace_id": "abc123",
  "access_id": "acc-789",
  "tenant": "hospital-x",
  "timestamp": "2026-03-15T14:22:05Z"
}
```

Access event 寫入獨立的 immutable storage（append-only log），跟 application log 分開的 pipeline 與 retention。

### Cross-service access chain

在 API gateway 入口產生 `access_id`，跟 `trace_id` 一起透過 context propagation 傳遞到所有下游服務。每個服務在產生 access event 時帶上這兩個 key。查詢時用 `access_id` 就能撈出一次存取操作在所有服務的完整軌跡，不需要手動拼接。

`trace_id` 用於關聯 operational 訊號（latency、error），`access_id` 用於關聯合規稽核。兩者可以相同也可以不同 — 關鍵是 access event 要同時帶兩個 key。

### 分層 retention 與 tenant-level policy

| 層級 | 儲存                                      | Retention                | 用途               |
| ---- | ----------------------------------------- | ------------------------ | ------------------ |
| Hot  | 搜尋引擎（Elasticsearch / Cloud Logging） | 90 天                    | 即時查詢、事故調查 |
| Warm | Object storage（壓縮）                    | 2 年                     | 定期稽核、合規查詢 |
| Cold | Archive storage（冰凍）                   | 6-7 年（依 tenant 法規） | 法規保留、法務調查 |

每個 tenant 在平台建立時設定法規要求的 retention 期限。Pipeline 根據 tenant tag 自動把 access event 路由到對應的 retention tier。Tenant A 的紀錄到第 6 年自動歸檔到 cold，tenant B 在 GDPR 目的屆滿時觸發刪除審核。

### 存取 log 中的 PII 處理

Access event 本身包含 `patient_id` 跟 `actor`，這些在存取紀錄中是必要資訊（「誰看了什麼」需要這兩個欄位）。處理方式是存取控制而非遮罩 — access event storage 的讀取權限限縮到 compliance team 跟 audit 角色，engineering team 的一般查詢權限無法看到這些欄位。

## 取捨

| 面向       | 統一 retention           | 分層 + tenant-level                   |
| ---------- | ------------------------ | ------------------------------------- |
| 實作複雜度 | 低                       | 高（routing 邏輯、多層 storage）      |
| 儲存成本   | 高（全部留最長）         | 可控（各層各自成本）                  |
| 合規精確度 | 低（過度保留或保留不足） | 高（對齊各 tenant 法規要求）          |
| 刪除能力   | 無法按 tenant 刪         | 可（GDPR right to erasure）           |
| 查詢效率   | 全量搜尋                 | Hot tier 秒級、Cold tier 分鐘到小時級 |

分層架構的最大風險是跨層查詢的延遲 — 稽核要求「給我 3 年前的存取紀錄」時，cold tier 的解凍時間可能是小時級。解法是在稽核週期前預先解凍相關 tenant 的 cold archive 到 warm tier。

## 回寫教材的連結

- [4.12 Audit Log Governance](/backend/04-observability/audit-log-governance/)：audit log 分離與 PII 治理。
- [4.18 Observability Operating Model](/backend/04-observability/observability-operating-model/)：access log pipeline 的 ownership 與 review cadence。
- [4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)：timestamp integrity 跟跨服務時序校正。
- [4.3 Tracing Context](/backend/04-observability/tracing-context/)：access_id 跟 trace_id 的 propagation 設計。

## 判讀徵兆

讀者在自己的系統看到以下訊號時，應該回讀本案例：

- 稽核問「使用者 X 在某段時間存取了什麼」，回答需要超過數小時的手動拼接
- 存取紀錄的 retention 跟法規要求不一致，但沒人確切量化差距
- Multi-tenant 環境中所有 tenant 共用同一個 retention policy，無法按法規區分
- 跨服務的存取事件無法自動關聯，需要靠 timestamp 近似比對
- PHI 相關的 log 跟一般 application log 存在同一個 storage，存取控制無法區隔
