---
title: "11.C44 Google AIP-151：長時操作實體化成 Operation resource"
date: 2026-07-03
description: "202 + 輪詢模式的系統化版本：回應型別先宣告、client 統一寫一套 polling、operation 生命週期明訂"
weight: 44
tags: ["backend", "api-design", "case-study", "long-running"]
---

這個案例的核心責任是提供長時操作介面模式的系統化規範。

## 觀察

AIP-151 規定長時方法回傳 `google.longrunning.Operation`（類比 Future / Promise）、必須標注 `response_type` 加 `metadata_type`；client 經 Operations service 輪詢；狀態欄位 `done` / `response` / `error`（`google.rpc.Status`）；操作約 30 天過期；validate-only 請求應直接回 `done=true` 的完成 operation、免除狀態管理。

## 判讀

把「進行中的工作」實體化成可 GET 的 resource、是 202 加 Location 輪詢模式的系統化版本：回應型別在 annotation 先宣告、client 可以統一寫一套 polling 邏輯。`done=true` 的 validate-only 條款示範「同一介面形狀涵蓋同步捷徑」的設計手法；30 天過期是 operation resource 生命週期需明訂的實例。

## 對應大綱

11.7 集合介面設計（長時操作段、anchor）、11.10 治理交叉（AIP 體系的一篇）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [AIP-151: Long-running operations（Google AIP）](https://google.aip.dev/151)
