---
title: "6.11 Migration Safety 與 DB Rollout"
date: 2026-05-01
description: "把 schema migration 從一次性事件變成可逆、可漸進的 rollout 流程"
weight: 11
tags: ["backend", "reliability"]
---

## 大綱

- migration 的核心約束：schema 變更必須跟程式碼版本相容
- expand / contract 模式：先擴展（雙寫 / 雙讀）、再收斂（移除舊欄位）
- 雙寫驗證：[shadow read](/backend/knowledge-cards/shadow-read/)、checksum 比對、流量採樣
- 線上 DDL 工具：pt-online-schema-change / gh-ost / Vitess online schema change
- 大表 migration 策略：批次、節流、避開 peak
- rollback 路徑設計：每階段必須可逆
- 跟 [6.10 contract testing](/backend/06-reliability/contract-testing/) 的整合：schema 契約驗證
- 跟 [6.8 release gate](/backend/06-reliability/release-gate/) 的整合：migration 可逆性作為 gate 條件
- 反模式：schema change 跟 code deploy 同 PR、rollback 變不可能；大表 ALTER 直接打、production 鎖表；新欄位 NOT NULL 無 default

## 概念定位

[Schema migration](/backend/knowledge-cards/schema-migration/) 是把 schema migration 從一次性事件變成可逆、可漸進的 rollout 流程，責任是避免資料結構變更直接把 production 推向不可回復狀態。

這一頁關心的是結構變更的節奏。當 code 與 schema 必須一起演進，安全做法不是追求一次到位，而是保留回退與相容窗口。

## 核心判讀

判讀 migration 時，先看每一步是否可逆，再看它是否能在 peak 外執行。

重點訊號包括：

- expand / contract 是否真的分開
- rollback 路徑是否先於 production 變更設計
- 大表操作是否有節流與 dry-run
- 雙寫 / shadow read 是否有一致性驗證

## 案例對照

- [Pinterest](/backend/06-reliability/cases/pinterest/_index.md)：資料結構與產品演進常同步變化。
- [GitHub](/backend/08-incident-response/cases/github/_index.md)：大規模平台 migration 容易把結構風險放大。
- [Stripe](/backend/06-reliability/cases/stripe/_index.md)：金流系統對 migration rollback 與一致性要求特別高。

## 交易類 migration 的特殊性

交易類 migration 同時承擔可用性跟正確性兩條軸。一般 schema migration 失敗的代價是停機、交易類失敗的代價額外包含結果不一致（重複扣款、訂單漏建、reconciliation 缺口）。守住兩條軸需要 idempotency + 漸進遷移 + 可回退發布 + 交易路徑可追溯四件事配合。

對應 [S1 Stripe Idempotency 與零停機遷移](/backend/06-reliability/cases/stripe/idempotency-and-zero-downtime-migration/)：揭露四個機制對應上述四件事 — idempotency key（同一交易重送如何得到同一結果）、expand/contract migration（資料變更如何與新舊版本共存）、canary + rollback gate（發版異常如何快速收斂）、transaction-path observability（交易路徑是否可追溯）。

交易類 migration 的關鍵 observables：

- duplicate request collapse ratio：重試是否被正確合併
- migration phase error drift：遷移各階段錯誤是否收斂
- canary transaction anomaly：小流量交易是否出現偏差
- payment trace consistency：trace 是否完整覆蓋交易關鍵欄位

把這四個機制視為「交易類 migration 的安全 baseline」、跟 [6.12 idempotency-replay](/backend/06-reliability/idempotency-replay/) 共用 idempotency key 設計、跟 [6.8 release gate 交易類變更段](/backend/06-reliability/release-gate/#交易類變更的-gate-設計) 共用 canary 條件。

交易類 migration 的反模式是把 migration 當「資料庫任務」獨立執行、跟 release gate 分離。正確做法是把 migration 跟 release 綁定治理、用同一套 evidence 跟 rollback 條件判讀。

## 下一步路由

- 01.6 [資料庫轉換實作](/backend/01-database/database-migration-playbook/)：雙寫、回填、切流與回滾
- 01.7 [Schema Migration Rollout 證據](/backend/01-database/schema-migration-rollout-evidence/)：把 migration plan 落成 [validation query](/backend/knowledge-cards/validation-query/)、evidence package、release gate 與 decision log
- 06.8 release gate：把可逆性放進放行條件
- 06.10 contract testing：先驗 schema 相容性
- 08.5 [post-incident review](/backend/knowledge-cards/post-incident-review/)：migration 類事故通常需要結構化復盤

## 判讀訊號

- migration 失敗只能 forward-fix、無 rollback 路徑
- 大表 ALTER 在 peak 時段執行造成鎖表
- 程式碼跟 schema 必須同步部署、deploy 失敗風險高
- 雙寫期間無一致性驗證、cutover 後才發現資料漂移
- migration 工具無 dry-run、production 才知道執行時間

## 交接路由

- 01.6 [資料庫轉換實作](/backend/01-database/database-migration-playbook/)：執行層流程
- 01.7 [Schema Migration Rollout 證據](/backend/01-database/schema-migration-rollout-evidence/)：production rollout evidence 與 gate 欄位
- 0.C4 [營運後技術轉換](/backend/00-service-selection/cases/post-scale-migration-language-tool-architecture/)：決策層判讀
- 06.7 DR / rollback：migration rollback 演練
- 06.8 release gate：可逆性檢查
- 06.10 contract testing：schema 契約驗證
- 08.5 [post-incident review](/backend/knowledge-cards/post-incident-review/)：migration 引發的事故型態
