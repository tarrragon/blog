---
title: "Authorization Middleware"
date: 2026-04-23
description: "說明請求進入 handler 前如何完成權限判斷"
weight: 0
---


Authorization Middleware 的核心概念是「在 request 進入業務處理前，先確認呼叫者能不能做這件事」。 可先對照 [Authorization](/backend/knowledge-cards/authorization/)。

## 概念位置

Authorization Middleware 位在 authentication 之後、業務 handler 之前。它依角色、資源或 tenant 來判斷可否操作。 可先對照 [Authorization](/backend/knowledge-cards/authorization/)。

## 可觀察訊號

系統需要 authorization middleware 的訊號是很多 handler 都在重複做權限檢查，且權限規則需要一致。

## 接近真實網路服務的例子

admin 操作、資源 owner 檢查、tenant boundary 檢查與欄位級權限，都常放在 authorization middleware。

## 設計責任

Authorization Middleware 要定義決策輸入、拒絕回應、稽核欄位與錯誤分類，不應把 policy 分散到各個 handler。
