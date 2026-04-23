---
title: "Data Reconciliation"
date: 2026-04-23
description: "說明多個資料來源不一致時如何比對、修復與留下證據"
weight: 87
---

Data reconciliation 的核心概念是「比對多個資料來源，找出差異並修復到可接受狀態」。它常用在付款對帳、資料遷移、事件漏處理、報表修復與第三方同步。

## 概念位置

Reconciliation 是 eventual consistency 的修復流程。即使系統設計了事件、retry 與 outbox，仍需要定期或事件後比對正式結果，修復漏送、重複或半成功。

## 可觀察訊號與例子

系統需要 reconciliation 的訊號是兩個系統都聲稱有狀態，但結果可能不同。付款 provider 顯示已扣款，訂單系統顯示未付款時，需要對帳流程判斷正式結果並修復訂單狀態。

## 設計責任

Reconciliation 要定義比對來源、優先權、差異分類、修復動作、audit 與人工介入條件。高風險資料要保留修復前後的證據。
