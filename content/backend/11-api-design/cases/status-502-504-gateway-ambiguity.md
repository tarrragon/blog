---
title: "11.C67 RFC 9110 502/504：gateway 只回報自己的觀察、不回報上游的執行狀態"
date: 2026-07-04
description: "502/504 定義只說 gateway 沒收到有效或及時回應、沒有欄位區分「請求沒送到」與「執行了但回應丟了」— retry 安全性相反的兩種情況拿到同一個 code"
weight: 67
tags: ["backend", "api-design", "case-study", "error-contract"]
---

這個案例的核心責任是提供 502/504 歧義的規範定義基礎：定義是 spec 事實、retry 安全歧義是從定義出發的推導（標明）。

## 觀察

RFC 9110 §15.6.3：「The 502 (Bad Gateway) status code indicates that the server, while acting as a gateway or proxy, received an invalid response from an inbound server it accessed while attempting to fulfill the request.」§15.6.5：「The 504 (Gateway Timeout) status code indicates that the server, while acting as a gateway or proxy, did not receive a timely response from an upstream server it needed to access in order to complete the request.」兩節全文僅此 —— 規範沒有任何欄位區分「上游根本沒收到請求」與「上游收到並執行了、只是回應沒回來或超時」。

## 判讀

（此段為推導、非 spec 明文。）spec 只定義 gateway 的觀察（沒收到有效或及時回應）、不定義上游的執行狀態。504 尤其如此：connect timeout（請求沒送到、retry 安全）跟 read timeout（請求已執行、對非冪等操作 retry 會重複執行）在 consumer 端拿到同一個 504 —— 兩種情況的 retry 安全性相反、status code 層無法區分。這是 status 表達力的第三種邊界形態：不是裝不下多個結果（C64）、也不是裝不下時間軸（C66）、是裝不下不確定性。緩解手段（idempotency key、上游去重）全在 status code 之外。

## 對應大綱

11.11 status 表達力邊界章「502/504 歧義」段、接收方重試決策章的 retry 安全合判段（連 11.8 冪等）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [HTTP Semantics §15.6.3 / §15.6.5（RFC 9110）](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.6.3) — 一手 IETF spec、Internet Standard。

## 二手來源與狀態標注

逐字原文以 rfc-editor 官方 .txt 取回核對（WebFetch 視窗截斷）。「歧義 → retry 安全性相反」的判讀無單一一手來源明文、正文引用標為從 spec 定義出發的通用推導。
