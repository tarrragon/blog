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
- 08.5 postmortem：migration 引發的事故型態
