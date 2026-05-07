---
title: "Stripe：Idempotency 與零停機遷移的交易安全設計"
date: 2026-05-07
description: "把 API 重試與資料遷移放在同一套安全模型，維持支付交易的一致結果。"
weight: 41
---

Stripe 案例的核心責任是確保交易語義在重試與變更中保持一致。支付系統的失效成本不只來自停機，還來自錯誤結果；因此可靠性設計要同時守住可用性與正確性。

## 問題場景

交易系統最常見的高風險組合是：客戶端重試、網路抖動、後端部署或資料遷移同時發生。若系統只處理單一失效，結果往往是可用但不一致，或者一致但無法持續交付。

idempotency key 與 zero-downtime migration 的組合，目標是讓這些變更在同一套邊界下可判讀。

## 決策機制

| 機制                           | 核心問題                     | 交付結果   |
| ------------------------------ | ---------------------------- | ---------- |
| Idempotency key                | 同一交易重送如何得到同一結果 | 重試安全   |
| Expand/contract migration      | 資料變更如何與新舊版本共存   | 漸進遷移   |
| Canary + rollback gate         | 發版異常如何快速收斂         | 可回復交付 |
| Transaction-path observability | 交易路徑是否可追溯           | 一致性證據 |

這組機制把「交易正確性」前移到 API 與遷移設計，而不是事後 reconciliation 才補救。

## 可觀測訊號

| 訊號                             | 判讀重點                       | 對應章節                                                          |
| -------------------------------- | ------------------------------ | ----------------------------------------------------------------- |
| duplicate request collapse ratio | 重試是否被正確合併             | [6.12](/backend/06-reliability/idempotency-replay/)               |
| migration phase error drift      | 遷移各階段錯誤是否收斂         | [6.11](/backend/06-reliability/migration-safety/)                 |
| canary transaction anomaly       | 小流量交易是否出現偏差         | [6.8](/backend/06-reliability/release-gate/)                      |
| payment trace consistency        | trace 是否完整覆蓋交易關鍵欄位 | [4.20](/backend/04-observability/observability-evidence-package/) |

## 常見陷阱

把 idempotency 實作成「只去重請求 ID」會漏掉交易語義。正確做法是讓 key 與業務操作邊界一致，並保留足夠證據以供重放與稽核判讀。另一個常見錯誤是把 migration 視為資料庫任務，沒有與 release gate 共同治理。

## 下一步路由

實作層先從 [6.12](/backend/06-reliability/idempotency-replay/) 定義重放語義，再到 [6.11](/backend/06-reliability/migration-safety/) 建立遷移節奏。發布控制對齊 [6.8](/backend/06-reliability/release-gate/)；事故時的交易影響評估對齊 [8.20](/backend/08-incident-response/customer-impact-assessment/)。
