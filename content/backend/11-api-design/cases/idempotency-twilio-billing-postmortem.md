---
title: "11.C45 Twilio 2013 計費事故：無冪等防線的重複扣款（反例）"
date: 2026-07-03
description: "反例：內部 retry 迴圈缺冪等閘門等效於無限重放、fail-safe 是金流 side effect 的斷路器"
weight: 45
tags: ["backend", "api-design", "case-study", "idempotency"]
---

這個案例的核心責任是提供冪等缺席的事故反例：冪等不只是對外 API header、內部 side-effect 動作同樣需要閘門。

## 觀察

Twilio 2013 年的 post-mortem：Redis master 重啟時讀錯設定、以自己的 slave 身份開機進入 read-only；餘額資料遺失歸零且無法寫回；auto-recharge 在「餘額為零、扣款成功、餘額寫不回去」的循環中對約 1.4% 客戶的信用卡重複扣款。修復含：餘額不可寫時禁止扣款與停權的 fail-safe、對獨立 double-bookkeeping 資料庫做即時驗證。

## 判讀

扣款動作的觸發條件（餘額低）在扣款後未被消除、等效於無限重放的非冪等操作。教學映射：冪等閘門的通用形式是「執行紀錄先寫、後執行」；fail-safe（狀態寫不進去就不准產生金流 side effect）是 write-path 依賴的斷路器。

## 對應大綱

11.8 API 層冪等設計（反例）、11.4 錯誤狀態下的降級決策交叉。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Billing Incident Post-Mortem（Twilio blog、2013）](https://www.twilio.com/en-us/blog/company/communications/billing-incident-post-mortem-breakdown-analysis-and-root-cause-html)
