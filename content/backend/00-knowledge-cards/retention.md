---
title: "Retention"
date: 2026-04-23
description: "說明資料或事件保留多久，以及保留期限如何影響重放與成本"
weight: 75
---

Retention 的核心概念是「資料或事件在系統中保留多久」。它影響 storage cost、audit、replay、debug、合規與資料刪除責任。

## 概念位置

Retention 連接資料生命週期與操作能力。Log、trace、queue message、event stream、backup、匯出檔案與 audit log 都需要不同保留期限。

## 可觀察訊號與例子

系統需要 retention 設計的訊號是事故排查或資料修復需要回看歷史。若 event stream 只保留 24 小時，三天前的錯誤就無法靠 replay 重建。

## 設計責任

Retention 要同時看成本、法規、資安、刪除權、備份與 replay 需求。高敏感資料的保留期限需要更嚴格的存取控制與 audit。
