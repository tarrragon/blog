---
title: "Authorization Middleware"
date: 2026-04-23
description: "說明請求進入 handler 前如何完成權限判斷"
weight: 1
---

Authorization Middleware 的核心概念是「在 request 進入業務處理前，先確認呼叫者能不能做這件事」。 可先對照 [Authorization](/backend/knowledge-cards/authorization/)。

## 跟其他概念的關係

Authorization Middleware 位在 authentication 之後、業務 handler 之前。它依角色、資源或 tenant 來判斷可否操作。 可先對照 [Authorization](/backend/knowledge-cards/authorization/)。

## 可觀察訊號

系統需要 authorization middleware 的訊號是很多 handler 都在重複做權限檢查，且權限規則需要一致。

## 接近真實網路服務的例子

admin 操作、資源 owner 檢查、tenant boundary 檢查與欄位級權限，都常放在 authorization middleware。

## 判斷條件與後果

Authorization Middleware 把權限決策集中在 handler 之前時，同一條規則只寫一次，每個 handler 套用的是同一個版本；policy 分散在各個 handler 時，新增的 handler 漏寫檢查就是一個越權入口，規則一改也要找出每一份副本。決策輸入（角色、資源、tenant）沒有定義清楚時，middleware 拿不到判斷所需的資料，這類判斷又退回 handler 裡各寫一份。拒絕回應沒有統一時，有的 handler 回 403、有的回 404，呼叫端與監控都無法一致地辨認被拒絕的請求；沒有稽核欄位時，被拒絕的越權嘗試留不下紀錄；錯誤沒有分類時，權限服務本身失效與請求被拒絕混成同一種結果。
