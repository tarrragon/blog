---
title: "BOLA / IDOR"
date: 2026-04-23
description: "說明物件層授權缺失如何讓使用者存取不屬於自己的資料"
weight: 112
---

BOLA / IDOR 的核心概念是「使用者透過修改物件 ID 存取未授權資源」。BOLA 是 Broken Object Level Authorization；IDOR 是 Insecure Direct Object Reference。

## 概念位置

BOLA 是 API 安全中常見的授權問題。Authentication 只能確認呼叫者身份；每次讀寫訂單、檔案、帳戶、發票或 tenant 資源時，仍要檢查該身份是否能操作該物件。

## 可觀察訊號與例子

系統需要 BOLA 防護的訊號是 API path 或 body 中包含資源 ID。使用者把 `/orders/1001` 改成 `/orders/1002` 時，系統必須確認 1002 是否屬於該使用者或其 tenant。

## 設計責任

BOLA 防護要在 usecase 或 policy 層檢查 resource ownership、tenant boundary 與角色權限。測試要覆蓋跨使用者、跨 tenant、低權限操作與猜測 ID。
