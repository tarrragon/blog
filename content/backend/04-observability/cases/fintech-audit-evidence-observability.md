---
title: "FinTech：審計證據鏈的可觀測性設計"
date: 2026-05-07
description: "把交易與存取事件轉成可回查證據，降低合規審核與事故判讀落差。"
weight: 1
tags: ["backend", "observability", "case-study"]
---

本案例的核心責任是讓審計證據與運維訊號共用同一套資料邊界。FinTech 場景下，觀測資料不只是除錯用途，也是合規證據基礎。

## 業務背景

一家處理線上支付的金融科技公司，每日交易量約 200 萬筆，涵蓋信用卡收單、轉帳與退款。每季有外部稽核查核交易處理的完整性與存取控制，事故發生時法務需要在 48 小時內提供特定交易的完整處理鏈證據。

初期系統把所有 log 寫到同一個 log group — application debug、request trace、交易狀態變更與使用者存取紀錄全混在一起。稽核人員要從數 TB 的 log 中撈出特定交易的完整軌跡，每次查詢耗時數小時。

## 技術挑戰

### Operational log 與 audit log 混合

Application log 記錄 debug 資訊（SQL timing、cache hit/miss、retry），audit log 記錄業務事件（交易建立、狀態變更、存取紀錄）。兩者混在同一個 pipeline 時，retention 策略互相衝突 — debug log 留 14 天夠用，但 audit log 法規要求保留 5 年。統一設成 5 年讓儲存成本暴增，統一設成 14 天則遺失合規證據。

### PII 暴露在 log 中

早期 log 直接印出 request body，信用卡號跟身分證字號散落在各種 log entry。稽核指出 PII 在 log 系統中的暴露面超過業務需要，但 log 已經寫入後無法回溯修改。

### Event correlation 斷裂

交易從建立到完成經過多個服務（checkout-api → payment-gateway → settlement → notification），但各服務的 log 使用不同的 correlation key。Checkout 用 `order_id`，payment-gateway 用 `payment_ref`，settlement 用自己的 `batch_id`。稽核要求「給我交易 X 的完整處理鏈」時，工程師需要手動在三個系統各自查詢再人工拼接。

## 解法

### Audit log 分離

把 audit event 獨立到專屬 pipeline：交易狀態變更、使用者存取、權限變動、退款操作各自產生結構化 audit event，寫入 immutable storage（append-only、禁止刪除與修改）。Operational log 維持 14 天 retention，audit log 走 5 年 retention + cold archive。

分離的判準是「這筆紀錄是否可能被稽核或法務要求提供」。是 → audit pipeline；否 → operational pipeline。灰色地帶（例如認證失敗 log）歸入 audit pipeline — 寧可多留不可少留。

### PII redaction pipeline

在 log ingestion 階段加入 redaction processor：信用卡號遮罩為末四碼、身分證字號完全移除、email 保留 domain 遮罩使用者名稱。Redaction 發生在寫入儲存之前，原始資料不落地。

需要完整 PII 的場景（如詐欺調查）走另一條授權存取管道，跟觀測 pipeline 分離。

### 統一 correlation key

所有服務在交易入口處產生 `trace_id` 和 `transaction_id`，兩個 key 同時寫入每一筆 audit event 和 operational log。稽核查詢用 `transaction_id` 就能撈出跨服務的完整處理鏈，不需要手動拼接。

## 取捨

| 面向       | 混合 pipeline                          | 分離 pipeline                              |
| ---------- | -------------------------------------- | ------------------------------------------ |
| 建置成本   | 低（一套 pipeline）                    | 中（兩套 pipeline + routing 邏輯）         |
| 儲存成本   | 高（全部用最長 retention）             | 可控（各自 retention）                     |
| 查詢效率   | 低（audit event 淹沒在 debug log 中）  | 高（audit 獨立查詢）                       |
| 合規風險   | 高（PII 暴露面大、retention 可能不足） | 低（PII redacted、retention 對齊法規）     |
| 維運複雜度 | 低                                     | 中（需維護 routing 規則與 redaction 規則） |

分離 pipeline 的最大成本在 routing 規則的維護 — 新服務上線時要確認 audit event 走對 pipeline。解法是在 SDK 層提供 `emit_audit_event()` 函式，讓 routing 在 producer 端決定，不依賴下游 pipeline 的內容判斷。

## 回寫教材的連結

- [4.12 Audit Log Governance](/backend/04-observability/audit-log-governance/)：audit log 分離的設計原則與 PII 治理。
- [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)：把 audit trail 包成可交接的 evidence package。
- [4.18 Observability Operating Model](/backend/04-observability/observability-operating-model/)：audit pipeline 的 ownership 歸 platform team 還是 compliance team。
- [4.3 Tracing Context](/backend/04-observability/tracing-context/)：跨服務 correlation key 的 propagation 設計。

## 判讀徵兆

讀者在自己的系統看到以下訊號時，應該回讀本案例：

- 稽核或法務要求提供某筆交易的完整處理鏈，工程師需要超過 1 小時才能拼出來
- Log retention 設定跟法規要求不一致，但沒人確切知道差多少
- PII 出現在 log search 結果中，但沒有系統性的遮罩機制
- Application log 跟 audit log 用同一套 retention policy，儲存成本持續上升但沒人敢縮短
- 事故後法務要證據，發現關鍵時段的 log 已經因為 retention 過期而被刪除
