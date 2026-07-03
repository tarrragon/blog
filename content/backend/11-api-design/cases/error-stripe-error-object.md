---
title: "11.C36 Stripe 錯誤物件：type / code / param 三層分離"
date: 2026-07-03
description: "路由層、分支層、UI 層做成正交欄位；冪等衝突列 first-class 錯誤型別；標準前自成一格的對照組"
weight: 36
tags: ["backend", "api-design", "case-study", "error-model"]
---

這個案例的核心責任是提供大型 API 錯誤模型的實作設計、跟 RFC 9457 形成「標準與大廠自訂並存」的對照。

## 觀察

Stripe 錯誤物件分四個 `type`（`api_error` / `card_error` / `idempotency_error` / `invalid_request_error`）；`code` 是細粒度機器碼、`decline_code` 透傳發卡行原因、`param` 指出出錯欄位、`message` 明示可直接顯示給終端使用者、附 `doc_url` 與 `request_log_url`。HTTP 402 專用於「參數合法但交易被拒」。

## 判讀

「路由層（type）、分支層（code）、UI 層（param + message）」做成三個正交欄位、client 端 error handling 各層各取所需。`idempotency_error` 列為 first-class type、顯示冪等衝突在支付 API 是預期常態、不是邊角。Stripe 早於 RFC 7807 生態自成一格 — 標準與自訂並存是錯誤格式爭論的現實背景。

## 對應大綱

11.4 錯誤模型設計（anchor）、11.8 API 層冪等交叉、錯誤格式爭論文章。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Errors（Stripe API reference）](https://docs.stripe.com/api/errors)
