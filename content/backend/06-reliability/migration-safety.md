---
title: "6.11 Migration Safety 與 DB Rollout"
date: 2026-05-01
description: "把 schema migration 從一次性事件變成可逆、可漸進的 rollout 流程"
weight: 11
---

## 大綱

- migration 的核心約束：schema 變更必須跟程式碼版本相容
- expand / contract 模式：先擴展（雙寫 / 雙讀）、再收斂（移除舊欄位）
- 雙寫驗證：shadow read、checksum 比對、流量採樣
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

## 下一步路由

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

- 06.7 DR / rollback：migration rollback 演練
- 06.8 release gate：可逆性檢查
- 06.10 contract testing：schema 契約驗證
- 08.5 [post-incident review](/backend/knowledge-cards/post-incident-review/)：migration 引發的事故型態
