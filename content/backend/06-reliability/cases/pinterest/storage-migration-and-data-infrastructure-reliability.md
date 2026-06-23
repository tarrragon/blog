---
title: "Pinterest：Storage Migration 與 Data Infrastructure Reliability"
date: 2026-06-23
description: "大規模儲存遷移的可靠性設計：用 dual-write、shadow read 與 staged cutover 讓 PB 級資料基礎設施變更可漸進、可驗證、可回退。"
weight: 42
tags: ["backend", "reliability", "case-study"]
---

Storage migration 的可靠性責任是讓資料基礎設施的變更可漸進、可驗證、可回退。PB 級資料的儲存引擎遷移（如 HBase → TiDB）牽涉 schema mapping、query pattern 差異與 consistency model 變更，任何一處不相容都會在 production 流量下被放大。

## 問題場景

Pinterest 的資料基礎設施服務數十億 pin、推薦系統與搜尋索引。當儲存引擎需要退役或升級時，直接 cutover 的風險在於所有不相容同時暴露 — query 語意差異、pagination 行為、null handling、ordering 規則都可能在切換瞬間衝擊線上流量。

漸進遷移的設計核心是把一次性 cutover 拆成可觀測的多階段流程，每個階段都有回退路徑。

## 決策機制

| 機制           | 核心問題                         | 交付結果       |
| -------------- | -------------------------------- | -------------- |
| Dual-write     | 新舊系統的寫入是否同步且完整     | 資料不遺失保證 |
| Shadow read    | 新舊系統的讀取結果是否一致       | 行為差異清單   |
| Reconciliation | 兩套系統的資料是否持續一致       | 一致性報告     |
| Staged cutover | 何時可以把流量從舊系統切到新系統 | 漸進切換節奏   |

Dual-write 確保遷移期間每筆寫入同時進入新舊系統。寫入失敗的處理策略決定資料完整性 — 若新系統寫入失敗是否 block 舊系統的寫入，取決於遷移階段（早期容許新系統 fail-open、接近 cutover 時需要 fail-close）。

Shadow read 在真實流量下比對新舊系統的查詢結果。比對維度包含回傳資料的完整性、排序、分頁邊界與 null 值處理。mismatch rate 是 cutover 可行性的核心判準 — rate 趨近零才能進入下一批切換。

Staged cutover 按 traffic percentage、data partition 或 use case 漸進切換。每一批觀察 mismatch rate、latency overhead 與 error rate，任一指標超門檻即回退到舊系統。

## 可觀測訊號

| 訊號                        | 判讀重點                 | 對應章節                                                       |
| --------------------------- | ------------------------ | -------------------------------------------------------------- |
| shadow read mismatch rate   | 新舊系統行為差異是否收斂 | [6.11](/backend/06-reliability/migration-safety/)              |
| dual-write latency overhead | 同步寫入是否拖累主路徑   | [6.13](/backend/06-reliability/performance-regression-gate/)   |
| reconciliation gap          | 兩套系統資料是否持續一致 | [6.23](/backend/06-reliability/verification-evidence-handoff/) |
| cutover rollback count      | 切換過程是否穩定         | [6.7](/backend/06-reliability/dr-rollback-rehearsal/)          |

## 常見陷阱

Shadow read 比對容易只看最終結果是否相同，忽略中間狀態的差異。pagination 的邊界行為、null 欄位的回傳語意、排序在 tie-breaking 時的規則 — 這些差異在主流程不明顯，但在邊界情境會爆發。reconciliation 需要覆蓋 edge case，包含空集合回傳、大量資料分頁與 concurrent write 衝突。

## 下一步路由

- [6.11 migration safety](/backend/06-reliability/migration-safety/)：storage migration 的 schema 相容與 rollout 策略
- [6.7 DR rollback rehearsal](/backend/06-reliability/dr-rollback-rehearsal/)：cutover 失敗時的 rollback 路徑
- [6.13 performance regression gate](/backend/06-reliability/performance-regression-gate/)：dual-write latency 作為 regression 偵測
- [6.23 verification evidence handoff](/backend/06-reliability/verification-evidence-handoff/)：reconciliation 結果作為 cutover 決策證據

## 引用源

- [Online Data Migration from HBase to TiDB with Zero Downtime](https://medium.com/pinterest-engineering/online-data-migration-from-hbase-to-tidb-with-zero-downtime-43f0fb474b84)
- [HBase Deprecation at Pinterest](https://medium.com/pinterest-engineering/hbase-deprecation-at-pinterest-8a99e6c8e6b7)
